<?php
class ControllerExtensionAnalyticsGtmEcommerce extends Controller {
	private $product_meta_cache = array();

	public function index() {
		return '';
	}

	public function headerAfter(&$route, &$data, &$output) {
		if (!$this->isEnabled() || !is_string($output) || $output === '') {
			return;
		}

		if (strpos($output, 'id="oc-gtm-ecommerce"') !== false) {
			return;
		}

		$gtm_id = $this->getGtmId();

		if ($gtm_id === '') {
			return;
		}

		$page_event = $this->getPageEvent();
		$has_gtm_loader = (strpos($output, 'googletagmanager.com/gtm.js') !== false);
		$head_block = $this->buildHeadBlock($gtm_id, $page_event, !$has_gtm_loader);

		$head_pos = strripos($output, '</head>');

		if ($head_pos !== false) {
			$output = substr_replace($output, $head_block . PHP_EOL, $head_pos, 0);
		} else {
			$output = $head_block . PHP_EOL . $output;
		}

		if (!$has_gtm_loader && strpos($output, 'googletagmanager.com/ns.html') === false) {
			$noscript = '<!-- Google Tag Manager (noscript) --><noscript><iframe src="https://www.googletagmanager.com/ns.html?id=' . htmlspecialchars($gtm_id, ENT_QUOTES, 'UTF-8') . '" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript><!-- End Google Tag Manager (noscript) -->';

			$output = preg_replace_callback(
				'/<body\b[^>]*>/i',
				function($matches) use ($noscript) {
					return $matches[0] . PHP_EOL . $noscript;
				},
				$output,
				1
			);
		}

		if ($page_event && isset($page_event['payload']['event']) && $page_event['payload']['event'] === 'gtm_purchase') {
			unset($this->session->data['gtm_ecommerce_purchase']);
		}
	}

	public function cartAddAfter(&$route, &$args, &$output) {
		if (!$this->isEventEnabled('add_to_cart') || !$this->routeMatchesCartAction($route, 'add')) {
			return;
		}

		$json = $this->getJsonResponse();

		if (!$json || empty($json['success'])) {
			return;
		}

		$product_id = $this->getRequestProductId($json);

		if (!$product_id) {
			return;
		}

		$quantity = isset($this->request->post['quantity']) ? (int)$this->request->post['quantity'] : 1;

		if ($quantity < 1) {
			$quantity = 1;
		}

		$options = (isset($this->request->post['option']) && is_array($this->request->post['option'])) ? $this->request->post['option'] : array();
		$cart_product = $this->findCartProduct($product_id, $options);

		if ($cart_product) {
			$item = $this->buildItemFromCartProduct($cart_product, $quantity);
		} else {
			$this->load->model('catalog/product');
			$product_info = $this->model_catalog_product->getProduct($product_id);

			if (!$product_info) {
				return;
			}

			$item = $this->buildItemFromProductInfo($product_info, $quantity);
		}

		$currency = $this->getCurrentCurrency();
		$value = $this->roundMoney((float)$item['price'] * (int)$item['quantity'], $currency);

		$json['gtm_ecommerce'] = array(
			'event'     => 'gtm_add_to_cart',
			'ga4_event' => 'add_to_cart',
			'ecommerce' => array(
				'currency' => $currency,
				'value'    => $value,
				'items'    => array($item)
			)
		);

		$this->setJsonResponse($json);
	}

	public function cartRemoveBefore(&$route, &$args) {
		if (!$this->isEventEnabled('remove_from_cart') || !$this->routeMatchesCartAction($route, 'remove')) {
			return;
		}

		$key = $this->getCartKeyFromRequest();

		if ($key === '') {
			return;
		}

		foreach ($this->cart->getProducts() as $product) {
			if ((string)$product['cart_id'] === $key) {
				$item = $this->buildItemFromCartProduct($product);
				$currency = $this->getCurrentCurrency();
				$value = $this->roundMoney((float)$item['price'] * (int)$item['quantity'], $currency);

				if (!isset($this->session->data['gtm_ecommerce_pending_remove']) || !is_array($this->session->data['gtm_ecommerce_pending_remove'])) {
					$this->session->data['gtm_ecommerce_pending_remove'] = array();
				}

				$this->session->data['gtm_ecommerce_pending_remove'][$key] = array(
					'event'     => 'gtm_remove_from_cart',
					'ga4_event' => 'remove_from_cart',
					'ecommerce' => array(
						'currency' => $currency,
						'value'    => $value,
						'items'    => array($item)
					)
				);

				break;
			}
		}
	}

	public function cartRemoveAfter(&$route, &$args, &$output) {
		if (!$this->isEventEnabled('remove_from_cart') || !$this->routeMatchesCartAction($route, 'remove')) {
			return;
		}

		$key = $this->getCartKeyFromRequest();

		if ($key === '' || empty($this->session->data['gtm_ecommerce_pending_remove'][$key])) {
			return;
		}

		$payload = $this->session->data['gtm_ecommerce_pending_remove'][$key];
		unset($this->session->data['gtm_ecommerce_pending_remove'][$key]);

		if (empty($this->session->data['gtm_ecommerce_pending_remove'])) {
			unset($this->session->data['gtm_ecommerce_pending_remove']);
		}

		$json = $this->getJsonResponse();

		if (!$json) {
			return;
		}

		$successful = !empty($json['success']) || (!empty($json['status']) && empty($json['error']));

		if (!$successful) {
			return;
		}

		$json['gtm_ecommerce'] = $payload;
		$this->setJsonResponse($json);
	}

	public function capturePurchase(&$route, &$args) {
		if (!$this->isEventEnabled('purchase') || empty($this->session->data['order_id'])) {
			return;
		}

		$order_id = (int)$this->session->data['order_id'];

		if ($order_id < 1) {
			return;
		}

		if (!empty($this->session->data['gtm_ecommerce_purchase']['ecommerce']['transaction_id']) &&
			(string)$this->session->data['gtm_ecommerce_purchase']['ecommerce']['transaction_id'] === (string)$order_id) {
			return;
		}

		$this->load->model('checkout/order');

		$order = $this->model_checkout_order->getOrder($order_id);

		if (!$order) {
			return;
		}

		$currency = $order['currency_code'];
		$currency_value = (float)$order['currency_value'];

		if ($currency_value <= 0) {
			$currency_value = (float)$this->currency->getValue($currency);
		}

		if ($currency_value <= 0) {
			$currency_value = 1;
		}

		$items = array();
		$value = 0.0;
		$index = 0;
		$order_products = $this->model_checkout_order->getOrderProducts($order_id);

		foreach ($order_products as $product) {
			$price = $this->moneyOrder((float)$product['price'], $currency, $currency_value);
			$quantity = max(1, (int)$product['quantity']);

			$item = array(
				'item_id'   => (string)$product['product_id'],
				'item_name' => $product['name'],
				'price'     => $price,
				'quantity'  => $quantity,
				'index'     => $index
			);

			if (!empty($order['store_name'])) {
				$item['affiliation'] = $order['store_name'];
			}

			$meta = $this->getProductMeta((int)$product['product_id']);

			if ($meta['brand'] !== '') {
				$item['item_brand'] = $meta['brand'];
			}

			if ($meta['category'] !== '') {
				$item['item_category'] = $meta['category'];
			}

			$options = $this->model_checkout_order->getOrderOptions($order_id, $product['order_product_id']);
			$variant = $this->buildVariant($options);

			if ($variant !== '') {
				$item['item_variant'] = $variant;
			}

			$items[] = $item;
			$value += $price * $quantity;
			$index++;
		}

		if (!$items) {
			return;
		}

		$shipping = 0.0;
		$tax = 0.0;
		$totals = $this->model_checkout_order->getOrderTotals($order_id);

		foreach ($totals as $total) {
			$code = isset($total['code']) ? (string)$total['code'] : '';
			$amount = $this->moneyOrder((float)$total['value'], $currency, $currency_value);

			if ($code === 'shipping') {
				$shipping += $amount;
			}

			if ($code === 'tax' || strpos($code, 'tax_') === 0) {
				$tax += $amount;
			}
		}

		$value = $this->roundMoney($value, $currency);
		$shipping = $this->roundMoney($shipping, $currency);
		$tax = $this->roundMoney($tax, $currency);

		$ecommerce = array(
			'transaction_id' => (string)$order_id,
			'value'          => $value,
			'tax'            => $tax,
			'shipping'       => $shipping,
			'currency'       => $currency,
			'items'          => $items
		);

		if (!empty($this->session->data['coupon']) && is_string($this->session->data['coupon'])) {
			$ecommerce['coupon'] = $this->session->data['coupon'];
		}

		$this->session->data['gtm_ecommerce_purchase'] = array(
			'event'     => 'gtm_purchase',
			'ga4_event' => 'purchase',
			'ecommerce' => $ecommerce
		);
	}

	private function buildHeadBlock($gtm_id, $page_event, $inject_gtm) {
		$script = '<!-- OC GTM Ecommerce 1.0.0 -->' . PHP_EOL;
		$script .= '<script id="oc-gtm-ecommerce">' . PHP_EOL;
		$script .= 'window.dataLayer = window.dataLayer || [];' . PHP_EOL;

		if ($inject_gtm) {
			$script .= "(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);})(window,document,'script','dataLayer'," . $this->jsonForJs($gtm_id) . ');' . PHP_EOL;
		}

		$script .= 'window.ocGtmEcommercePush = window.ocGtmEcommercePush || function(payload){if(!payload){return;}window.dataLayer=window.dataLayer||[];window.dataLayer.push({ecommerce:null});window.dataLayer.push(payload);};' . PHP_EOL;

		if ($page_event && !empty($page_event['payload'])) {
			$payload_json = $this->jsonForJs($page_event['payload']);

			if (!empty($page_event['dedupe_key'])) {
				$key_json = $this->jsonForJs($page_event['dedupe_key']);
				$script .= '(function(){var p=' . $payload_json . ',k=' . $key_json . ',send=true;try{if(window.sessionStorage&&sessionStorage.getItem(k)){send=false;}else if(window.sessionStorage){sessionStorage.setItem(k,"1");}}catch(e){}if(send){window.ocGtmEcommercePush(p);}})();' . PHP_EOL;
			} else {
				$script .= 'window.ocGtmEcommercePush(' . $payload_json . ');' . PHP_EOL;
			}
		}

		if ($this->config->get('analytics_gtm_ecommerce_ecommerce_status') &&
			($this->config->get('analytics_gtm_ecommerce_track_add_to_cart') || $this->config->get('analytics_gtm_ecommerce_track_remove_from_cart'))) {
			$script .= $this->buildAjaxHookScript();
		}

		$script .= '</script>' . PHP_EOL;
		$script .= '<!-- /OC GTM Ecommerce 1.0.0 -->';

		return $script;
	}

	private function buildAjaxHookScript() {
		$js = <<<'JS'
window.ocGtmEcommerceConsumeResponse = window.ocGtmEcommerceConsumeResponse || function(body){
	try {
		var json = body;
		if (typeof body === 'string') {
			if (!body) { return; }
			json = JSON.parse(body);
		}
		if (json && json.gtm_ecommerce) {
			window.ocGtmEcommercePush(json.gtm_ecommerce);
		}
	} catch (e) {}
};
(function(){
	if (window.XMLHttpRequest && !window.__ocGtmEcommerceXhrHooked) {
		window.__ocGtmEcommerceXhrHooked = true;
		var originalOpen = XMLHttpRequest.prototype.open;
		var originalSend = XMLHttpRequest.prototype.send;

		XMLHttpRequest.prototype.open = function(method, url) {
			this.__ocGtmEcommerceUrl = url || '';
			return originalOpen.apply(this, arguments);
		};

		XMLHttpRequest.prototype.send = function() {
			var xhr = this;
			xhr.addEventListener('load', function() {
				if (xhr.status >= 200 && xhr.status < 400) {
					if (xhr.responseType === 'json') {
						window.ocGtmEcommerceConsumeResponse(xhr.response);
					} else {
						window.ocGtmEcommerceConsumeResponse(xhr.responseText);
					}
				}
			}, false);
			return originalSend.apply(this, arguments);
		};
	}

	if (window.fetch && !window.__ocGtmEcommerceFetchHooked) {
		window.__ocGtmEcommerceFetchHooked = true;
		var originalFetch = window.fetch;

		window.fetch = function() {
			return originalFetch.apply(this, arguments).then(function(response) {
				try {
					var clone = response.clone();
					clone.json().then(function(json) {
						window.ocGtmEcommerceConsumeResponse(json);
					}).catch(function(){});
				} catch (e) {}
				return response;
			});
		};
	}
})();
JS;

		return $js . PHP_EOL;
	}

	private function getPageEvent() {
		if (!$this->config->get('analytics_gtm_ecommerce_ecommerce_status')) {
			return null;
		}

		$route = isset($this->request->get['route']) ? (string)$this->request->get['route'] : 'common/home';

		if ($this->isSuccessRoute($route) && $this->isEventEnabled('purchase') && !empty($this->session->data['gtm_ecommerce_purchase'])) {
			return array(
				'payload'    => $this->session->data['gtm_ecommerce_purchase'],
				'dedupe_key' => ''
			);
		}

		if ($route === 'product/product' && $this->isEventEnabled('view_item') && !empty($this->request->get['product_id'])) {
			$this->load->model('catalog/product');
			$product_info = $this->model_catalog_product->getProduct((int)$this->request->get['product_id']);

			if ($product_info) {
				$item = $this->buildItemFromProductInfo($product_info, 1);
				$currency = $this->getCurrentCurrency();

				return array(
					'payload' => array(
						'event'     => 'gtm_view_item',
						'ga4_event' => 'view_item',
						'ecommerce' => array(
							'currency' => $currency,
							'value'    => $this->roundMoney((float)$item['price'], $currency),
							'items'    => array($item)
						)
					),
					'dedupe_key' => ''
				);
			}
		}

		if (($route === 'checkout/cart' || $route === 'journal3/cart') && $this->isEventEnabled('view_cart')) {
			$payload = $this->buildCartPayload('gtm_view_cart', 'view_cart');

			if ($payload) {
				return array('payload' => $payload, 'dedupe_key' => '');
			}
		}

		if ($this->isCheckoutPageRoute($route) && $this->isEventEnabled('begin_checkout')) {
			$payload = $this->buildCartPayload('gtm_begin_checkout', 'begin_checkout');

			if ($payload) {
				return array(
					'payload'    => $payload,
					'dedupe_key' => 'oc_gtm_begin_checkout_' . $this->getCartFingerprint()
				);
			}
		}

		return null;
	}

	private function buildCartPayload($event, $ga4_event) {
		$products = $this->cart->getProducts();

		if (!$products) {
			return null;
		}

		$items = array();
		$value = 0.0;
		$currency = $this->getCurrentCurrency();
		$index = 0;

		foreach ($products as $product) {
			$item = $this->buildItemFromCartProduct($product);
			$item['index'] = $index;

			$items[] = $item;
			$value += (float)$item['price'] * (int)$item['quantity'];
			$index++;
		}

		return array(
			'event'     => $event,
			'ga4_event' => $ga4_event,
			'ecommerce' => array(
				'currency' => $currency,
				'value'    => $this->roundMoney($value, $currency),
				'items'    => $items
			)
		);
	}

	private function buildItemFromProductInfo($product_info, $quantity) {
		$regular = (float)$product_info['price'];
		$effective = $regular;

		if (array_key_exists('special', $product_info) && $product_info['special'] !== false && $product_info['special'] !== null) {
			$effective = (float)$product_info['special'];
		}

		$price = $this->moneyCurrent($effective);
		$item = array(
			'item_id'   => (string)$product_info['product_id'],
			'item_name' => $product_info['name'],
			'price'     => $price,
			'quantity'  => max(1, (int)$quantity)
		);

		$regular_price = $this->moneyCurrent($regular);
		$discount = $this->roundMoney($regular_price - $price, $this->getCurrentCurrency());

		if ($discount > 0) {
			$item['discount'] = $discount;
		}

		$meta = $this->getProductMeta((int)$product_info['product_id']);

		if ($meta['brand'] !== '') {
			$item['item_brand'] = $meta['brand'];
		}

		if ($meta['category'] !== '') {
			$item['item_category'] = $meta['category'];
		}

		$affiliation = (string)$this->config->get('config_name');

		if ($affiliation !== '') {
			$item['affiliation'] = $affiliation;
		}

		return $item;
	}

	private function buildItemFromCartProduct($product, $quantity_override = null) {
		$quantity = ($quantity_override === null) ? (int)$product['quantity'] : (int)$quantity_override;
		$quantity = max(1, $quantity);

		$item = array(
			'item_id'   => (string)$product['product_id'],
			'item_name' => $product['name'],
			'price'     => $this->moneyCurrent((float)$product['price']),
			'quantity'  => $quantity
		);

		$variant = isset($product['option']) ? $this->buildVariant($product['option']) : '';

		if ($variant !== '') {
			$item['item_variant'] = $variant;
		}

		$meta = $this->getProductMeta((int)$product['product_id']);

		if ($meta['brand'] !== '') {
			$item['item_brand'] = $meta['brand'];
		}

		if ($meta['category'] !== '') {
			$item['item_category'] = $meta['category'];
		}

		$affiliation = (string)$this->config->get('config_name');

		if ($affiliation !== '') {
			$item['affiliation'] = $affiliation;
		}

		return $item;
	}

	private function getProductMeta($product_id) {
		$product_id = (int)$product_id;

		if (isset($this->product_meta_cache[$product_id])) {
			return $this->product_meta_cache[$product_id];
		}

		$meta = array('brand' => '', 'category' => '');

		$this->load->model('catalog/product');
		$product_info = $this->model_catalog_product->getProduct($product_id);

		if ($product_info && !empty($product_info['manufacturer'])) {
			$meta['brand'] = $product_info['manufacturer'];
		}

		$query = $this->db->query(
			"SELECT cd.name FROM " . DB_PREFIX . "product_to_category p2c " .
			"LEFT JOIN " . DB_PREFIX . "category_description cd ON (cd.category_id = p2c.category_id) " .
			"WHERE p2c.product_id = '" . $product_id . "' " .
			"AND cd.language_id = '" . (int)$this->config->get('config_language_id') . "' " .
			"ORDER BY p2c.category_id ASC LIMIT 1"
		);

		if ($query->num_rows && !empty($query->row['name'])) {
			$meta['category'] = $query->row['name'];
		}

		$this->product_meta_cache[$product_id] = $meta;

		return $meta;
	}

	private function buildVariant($options) {
		if (!is_array($options) || !$options) {
			return '';
		}

		$parts = array();

		foreach ($options as $option) {
			$name = isset($option['name']) ? trim((string)$option['name']) : '';
			$value = isset($option['value']) ? trim((string)$option['value']) : '';

			if ($name !== '' && $value !== '') {
				$parts[] = $name . ': ' . $value;
			}
		}

		return implode(' | ', $parts);
	}

	private function findCartProduct($product_id, $requested_options) {
		$fallback = null;

		foreach ($this->cart->getProducts() as $product) {
			if ((int)$product['product_id'] !== (int)$product_id) {
				continue;
			}

			$fallback = $product;

			if ($this->optionsMatch(isset($product['option']) ? $product['option'] : array(), $requested_options)) {
				return $product;
			}
		}

		return $fallback;
	}

	private function optionsMatch($cart_options, $requested_options) {
		if (!$requested_options) {
			return !$cart_options;
		}

		if (!is_array($cart_options)) {
			return false;
		}

		foreach ($requested_options as $product_option_id => $requested_value) {
			$requested_values = is_array($requested_value) ? $requested_value : array($requested_value);

			foreach ($requested_values as $value) {
				$found = false;

				foreach ($cart_options as $cart_option) {
					if ((int)$cart_option['product_option_id'] !== (int)$product_option_id) {
						continue;
					}

					if (isset($cart_option['product_option_value_id']) && (string)$cart_option['product_option_value_id'] === (string)$value) {
						$found = true;
						break;
					}

					if (isset($cart_option['value']) && (string)$cart_option['value'] === (string)$value) {
						$found = true;
						break;
					}
				}

				if (!$found) {
					return false;
				}
			}
		}

		return true;
	}

	private function getJsonResponse() {
		$body = $this->response->getOutput();

		if (!is_string($body) || $body === '') {
			return null;
		}

		$json = json_decode($body, true);

		return is_array($json) ? $json : null;
	}

	private function setJsonResponse($json) {
		$this->response->setOutput(json_encode($json));
	}

	private function getRequestProductId($json = array()) {
		if (!empty($this->request->post['product_id'])) {
			return (int)$this->request->post['product_id'];
		}

		if (!empty($this->request->get['product_id'])) {
			return (int)$this->request->get['product_id'];
		}

		if (!empty($json['product_id'])) {
			return (int)$json['product_id'];
		}

		return 0;
	}

	private function getCartKeyFromRequest() {
		if (isset($this->request->post['key'])) {
			return (string)$this->request->post['key'];
		}

		if (isset($this->request->post['cart_id'])) {
			return (string)$this->request->post['cart_id'];
		}

		return '';
	}

	private function routeMatchesCartAction($route, $action) {
		return (bool)preg_match('#(^|/)cart/' . preg_quote($action, '#') . '$#', (string)$route);
	}

	private function isSuccessRoute($route) {
		if ($route === 'checkout/success') {
			return true;
		}

		return (strpos($route, 'checkout') !== false && preg_match('#(^|/)success$#', $route));
	}

	private function isCheckoutPageRoute($route) {
		if ($route === 'checkout/checkout') {
			return true;
		}

		if ($route === 'journal3/checkout' || $route === 'journal3/checkout/checkout') {
			return true;
		}

		return false;
	}

	private function getCartFingerprint() {
		$fingerprint = array();

		foreach ($this->cart->getProducts() as $product) {
			$fingerprint[] = array(
				'cart_id'    => (string)$product['cart_id'],
				'product_id' => (int)$product['product_id'],
				'quantity'   => (int)$product['quantity'],
				'price'      => (float)$product['price']
			);
		}

		return hash('sha256', json_encode($fingerprint));
	}

	private function moneyCurrent($amount) {
		$currency = $this->getCurrentCurrency();
		return (float)$this->currency->format((float)$amount, $currency, '', false);
	}

	private function moneyOrder($amount, $currency, $currency_value) {
		return (float)$this->currency->format((float)$amount, $currency, (float)$currency_value, false);
	}

	private function roundMoney($value, $currency) {
		$decimals = (int)$this->currency->getDecimalPlace($currency);
		return round((float)$value, $decimals);
	}

	private function getCurrentCurrency() {
		if (!empty($this->session->data['currency'])) {
			return (string)$this->session->data['currency'];
		}

		return (string)$this->config->get('config_currency');
	}

	private function getGtmId() {
		$gtm_id = strtoupper(trim((string)$this->config->get('analytics_gtm_ecommerce_gtm_id')));

		if (!preg_match('/^GTM-[A-Z0-9]+$/', $gtm_id)) {
			return '';
		}

		return $gtm_id;
	}

	private function isEnabled() {
		return (bool)$this->config->get('analytics_gtm_ecommerce_status');
	}

	private function isEventEnabled($event) {
		if (!$this->isEnabled() || !$this->config->get('analytics_gtm_ecommerce_ecommerce_status')) {
			return false;
		}

		$map = array(
			'view_item'        => 'analytics_gtm_ecommerce_track_view_item',
			'add_to_cart'      => 'analytics_gtm_ecommerce_track_add_to_cart',
			'remove_from_cart' => 'analytics_gtm_ecommerce_track_remove_from_cart',
			'view_cart'        => 'analytics_gtm_ecommerce_track_view_cart',
			'begin_checkout'   => 'analytics_gtm_ecommerce_track_begin_checkout',
			'purchase'         => 'analytics_gtm_ecommerce_track_purchase'
		);

		return isset($map[$event]) && (bool)$this->config->get($map[$event]);
	}

	private function jsonForJs($value) {
		return json_encode($value, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT);
	}
}
