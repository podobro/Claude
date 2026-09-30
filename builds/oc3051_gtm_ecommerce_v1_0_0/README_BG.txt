Google Tag Manager + GA4 Ecommerce for OpenCart 3.0.5.1
Version: 1.0.0

ОБХВАТ
- OpenCart 3.0.5.1.
- PHP 8.5 compatible coding style (без deprecated dynamic properties / legacy constructor patterns).
- Analytics extension, използва OpenCart Events; не редактира core или theme файлове.
- Multi-store: отделен Status и GTM Container ID за всеки store.
- GTM loader + noscript.
- Защита от двойно зареждане на стандартен GTM loader.
- Generic dataLayer events + поле ga4_event.

ECOMMERCE EVENTS
gtm_view_item        -> ga4_event: view_item
gtm_add_to_cart      -> ga4_event: add_to_cart
gtm_remove_from_cart -> ga4_event: remove_from_cart
gtm_view_cart        -> ga4_event: view_cart
gtm_begin_checkout   -> ga4_event: begin_checkout
gtm_purchase         -> ga4_event: purchase

DATA FORMAT
Преди всяко ecommerce събитие модулът подава:
dataLayer.push({ecommerce: null});

След това:
dataLayer.push({
  event: "gtm_add_to_cart",
  ga4_event: "add_to_cart",
  ecommerce: {
    currency: "EUR",
    value: 12.50,
    items: [{
      item_id: "123",
      item_name: "Product",
      price: 12.50,
      quantity: 1
    }]
  }
});

PURCHASE
- transaction_id = OpenCart order_id.
- currency = валутата на поръчката.
- value = sum(price * quantity) за order products; не включва shipping и tax.
- shipping и tax са отделни event-level параметри.
- items[] се взимат от order_product, за да не зависят от вече изчистената количка.
- purchase snapshot се прави BEFORE checkout/success да изтрие order_id от session.
- Не се изпращат имейл, телефон, име, адрес или други PII.

AJAX CART
- add_to_cart се добавя към успешния JSON response от cart/add.
- remove_from_cart snapshot-ва реда преди remove и добавя събитието само към успешния JSON response.
- В header има XHR + fetch listener, който взима само gtm_ecommerce payload от успешния response.
- Работи със стандартните OpenCart cart routes и с routes, завършващи на /cart/add и /cart/remove.

THEME / CHECKOUT
- Инжекцията е върху rendered common/header чрез OpenCart Event, а не чрез Twig OCMOD.
- Това намалява зависимостта от theme.
- begin_checkout: стандартен checkout/checkout; добавена е базова поддръжка и за journal3/checkout и journal3/checkout/checkout.
- purchase: стандартен checkout/success.

ИНСТАЛАЦИЯ
1. Admin -> Extensions -> Installer.
2. Качи oc3051_gtm_ecommerce_v1.0.0.ocmod.zip.
3. Admin -> Extensions -> Extensions -> избери Analytics.
4. Инсталирай "Google Tag Manager + GA4 Ecommerce".
5. Натисни Edit за конкретния store.
6. Въведи GTM ID (пример GTM-ABC1234), Enable и Save.
7. За всеки допълнителен store повтори настройката с неговия GTM ID.

Не е необходимо Extensions -> Modifications -> Refresh, защото пакетът не използва OCMOD modification XML.

GTM НАСТРОЙКА
Препоръчана схема:
- Trigger: Custom Event за gtm_view_item, gtm_add_to_cart, gtm_remove_from_cart, gtm_view_cart, gtm_begin_checkout, gtm_purchase
  ИЛИ един regex trigger: ^gtm_(view_item|add_to_cart|remove_from_cart|view_cart|begin_checkout|purchase)$
- Data Layer Variable: ga4_event
- GA4 Event Name: {{DLV - ga4_event}}
- Ecommerce параметрите се четат от ecommerce.* / items[].

CONSENT MODE
Тази версия умишлено НЕ задава Consent Mode defaults и НЕ променя cookie consent.
Причина: да не презапише CMP / cookie banner на магазина.
Consent Mode v2 може да бъде добавен като отделна, opt-in функционалност.

ВАЖНО
- Ако друга тема/модул вече зарежда standard googletagmanager.com/gtm.js, модулът не зарежда втори GTM loader, но продължава да подава ecommerce dataLayer.
- При наличие на друг ecommerce tracking модул го изключи, за да няма двойни events.
- item_id в v1.0.0 е OpenCart product_id.
- item_category е първата присвоена OpenCart категория.
- item_variant съдържа избраните product options, когато са налични.
- Количка с промяна само на quantity чрез cart/edit не генерира отделен incremental add/remove event във v1.0.0; следващият view_cart / begin_checkout съдържа актуалните количества.

ТЕСТ
В Browser Console:
window.dataLayer

Очаквани generic events:
gtm_view_item
gtm_add_to_cart
gtm_remove_from_cart
gtm_view_cart
gtm_begin_checkout
gtm_purchase

Провери и в GTM Preview / Tag Assistant.
