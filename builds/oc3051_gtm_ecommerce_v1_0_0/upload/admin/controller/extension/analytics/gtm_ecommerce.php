<?php
class ControllerExtensionAnalyticsGtmEcommerce extends Controller {
	private $error = array();

	public function index() {
		$this->load->language('extension/analytics/gtm_ecommerce');

		$this->document->setTitle($this->language->get('heading_title'));

		$this->load->model('setting/setting');
		$this->load->model('setting/store');

		$store_id = isset($this->request->get['store_id']) ? (int)$this->request->get['store_id'] : 0;
		$defaults = $this->getDefaults();

		if (($this->request->server['REQUEST_METHOD'] == 'POST') && $this->validate()) {
			$post = $this->request->post;

			$post['analytics_gtm_ecommerce_gtm_id'] = strtoupper(trim((string)$post['analytics_gtm_ecommerce_gtm_id']));

			foreach ($defaults as $key => $default) {
				if (!array_key_exists($key, $post)) {
					$post[$key] = $default;
				}
			}

			$this->model_setting_setting->editSetting('analytics_gtm_ecommerce', $post, $store_id);

			$this->session->data['success'] = $this->language->get('text_success');

			$this->response->redirect($this->url->link('marketplace/extension', 'user_token=' . $this->session->data['user_token'] . '&type=analytics', true));
		}

		$data['error_warning'] = isset($this->error['warning']) ? $this->error['warning'] : '';
		$data['error_gtm_id'] = isset($this->error['gtm_id']) ? $this->error['gtm_id'] : '';

		$data['breadcrumbs'] = array();

		$data['breadcrumbs'][] = array(
			'text' => $this->language->get('text_home'),
			'href' => $this->url->link('common/dashboard', 'user_token=' . $this->session->data['user_token'], true)
		);

		$data['breadcrumbs'][] = array(
			'text' => $this->language->get('text_extension'),
			'href' => $this->url->link('marketplace/extension', 'user_token=' . $this->session->data['user_token'] . '&type=analytics', true)
		);

		$data['breadcrumbs'][] = array(
			'text' => $this->language->get('heading_title'),
			'href' => $this->url->link('extension/analytics/gtm_ecommerce', 'user_token=' . $this->session->data['user_token'] . '&store_id=' . $store_id, true)
		);

		$data['action'] = $this->url->link('extension/analytics/gtm_ecommerce', 'user_token=' . $this->session->data['user_token'] . '&store_id=' . $store_id, true);
		$data['cancel'] = $this->url->link('marketplace/extension', 'user_token=' . $this->session->data['user_token'] . '&type=analytics', true);

		$data['store_id'] = $store_id;
		$data['stores'] = array();

		$data['stores'][] = array(
			'store_id' => 0,
			'name'     => $this->config->get('config_name') . ' (' . $this->language->get('text_default') . ')',
			'href'     => $this->url->link('extension/analytics/gtm_ecommerce', 'user_token=' . $this->session->data['user_token'] . '&store_id=0', true)
		);

		foreach ($this->model_setting_store->getStores() as $store) {
			$data['stores'][] = array(
				'store_id' => (int)$store['store_id'],
				'name'     => $store['name'],
				'href'     => $this->url->link('extension/analytics/gtm_ecommerce', 'user_token=' . $this->session->data['user_token'] . '&store_id=' . (int)$store['store_id'], true)
			);
		}

		$settings = $this->model_setting_setting->getSetting('analytics_gtm_ecommerce', $store_id);

		foreach ($defaults as $key => $default) {
			if (isset($this->request->post[$key])) {
				$data[$key] = $this->request->post[$key];
			} elseif (array_key_exists($key, $settings)) {
				$data[$key] = $settings[$key];
			} else {
				$data[$key] = $default;
			}
		}

		$data['header'] = $this->load->controller('common/header');
		$data['column_left'] = $this->load->controller('common/column_left');
		$data['footer'] = $this->load->controller('common/footer');

		$this->response->setOutput($this->load->view('extension/analytics/gtm_ecommerce', $data));
	}

	protected function validate() {
		if (!$this->user->hasPermission('modify', 'extension/analytics/gtm_ecommerce')) {
			$this->error['warning'] = $this->language->get('error_permission');
		}

		$status = !empty($this->request->post['analytics_gtm_ecommerce_status']);
		$gtm_id = isset($this->request->post['analytics_gtm_ecommerce_gtm_id']) ? strtoupper(trim((string)$this->request->post['analytics_gtm_ecommerce_gtm_id'])) : '';

		if ($status && $gtm_id === '') {
			$this->error['gtm_id'] = $this->language->get('error_gtm_id_required');
		} elseif ($gtm_id !== '' && !preg_match('/^GTM-[A-Z0-9]+$/', $gtm_id)) {
			$this->error['gtm_id'] = $this->language->get('error_gtm_id_invalid');
		}

		return !$this->error;
	}

	public function install() {
		$this->load->model('setting/event');
		$this->load->model('setting/setting');

		$this->model_setting_event->deleteEventByCode('gtm_ecommerce');

		$this->model_setting_event->addEvent(
			'gtm_ecommerce',
			'catalog/view/common/header/after',
			'extension/analytics/gtm_ecommerce/headerAfter',
			1,
			0
		);

		$this->model_setting_event->addEvent(
			'gtm_ecommerce',
			'catalog/controller/checkout/success/before',
			'extension/analytics/gtm_ecommerce/capturePurchase',
			1,
			0
		);

		$this->model_setting_event->addEvent(
			'gtm_ecommerce',
			'catalog/controller/*/cart/add/after',
			'extension/analytics/gtm_ecommerce/cartAddAfter',
			1,
			0
		);

		$this->model_setting_event->addEvent(
			'gtm_ecommerce',
			'catalog/controller/*/cart/remove/before',
			'extension/analytics/gtm_ecommerce/cartRemoveBefore',
			1,
			0
		);

		$this->model_setting_event->addEvent(
			'gtm_ecommerce',
			'catalog/controller/*/cart/remove/after',
			'extension/analytics/gtm_ecommerce/cartRemoveAfter',
			1,
			0
		);

		$existing = $this->model_setting_setting->getSetting('analytics_gtm_ecommerce', 0);

		if (!$existing) {
			$this->model_setting_setting->editSetting('analytics_gtm_ecommerce', $this->getDefaults(), 0);
		}
	}

	public function uninstall() {
		$this->load->model('setting/event');
		$this->model_setting_event->deleteEventByCode('gtm_ecommerce');
	}

	private function getDefaults() {
		return array(
			'analytics_gtm_ecommerce_status'                 => 0,
			'analytics_gtm_ecommerce_gtm_id'                 => '',
			'analytics_gtm_ecommerce_ecommerce_status'       => 1,
			'analytics_gtm_ecommerce_track_view_item'        => 1,
			'analytics_gtm_ecommerce_track_add_to_cart'      => 1,
			'analytics_gtm_ecommerce_track_remove_from_cart' => 1,
			'analytics_gtm_ecommerce_track_view_cart'        => 1,
			'analytics_gtm_ecommerce_track_begin_checkout'   => 1,
			'analytics_gtm_ecommerce_track_purchase'         => 1
		);
	}
}
