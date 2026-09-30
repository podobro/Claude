<?php
// Heading
$_['heading_title'] = 'Google Tag Manager + GA4 Ecommerce';

// Text
$_['text_extension'] = 'Разширения';
$_['text_success'] = 'Успешно променихте настройките на Google Tag Manager + GA4 Ecommerce!';
$_['text_edit'] = 'Настройки на Google Tag Manager + GA4 Ecommerce';
$_['text_default'] = 'Основен';
$_['text_general'] = 'Основни';
$_['text_ecommerce'] = 'Ecommerce dataLayer';
$_['text_information'] = 'Разширението използва OpenCart Events и не променя core или файлове на темата. Ecommerce събитията използват generic event име плюс поле ga4_event.';
$_['text_duplicate'] = 'Защита от дублиране: ако в генерирания header вече има стандартен GTM loader, разширението няма да зареди втори. Ecommerce dataLayer събитията ще продължат да се подават.';
$_['text_consent'] = 'Consent: тази версия не задава и не презаписва Consent Mode. Управлението на съгласието остава в CMP / cookie-consent решението на магазина.';
$_['text_event_mapping'] = 'Съответствие на събитията';

// Entry
$_['entry_store'] = 'Магазин';
$_['entry_status'] = 'Статус';
$_['entry_gtm_id'] = 'GTM Container ID';
$_['entry_ecommerce_status'] = 'Ecommerce проследяване';
$_['entry_view_item'] = 'Преглед на продукт';
$_['entry_add_to_cart'] = 'Добавяне в количката';
$_['entry_remove_from_cart'] = 'Премахване от количката';
$_['entry_view_cart'] = 'Преглед на количката';
$_['entry_begin_checkout'] = 'Начало на поръчката';
$_['entry_purchase'] = 'Покупка';

// Help
$_['help_store'] = 'Всеки store може да използва различен GTM Container ID и независими настройки.';
$_['help_gtm_id'] = 'Пример: GTM-ABC1234. ID-то се записва отделно за всеки OpenCart store.';
$_['help_ecommerce'] = 'Подава ecommerce данни към window.dataLayer. Google Analytics се конфигурира в Google Tag Manager.';
$_['help_event_mapping'] = 'Generic event -> ga4_event: gtm_view_item -> view_item, gtm_add_to_cart -> add_to_cart, gtm_remove_from_cart -> remove_from_cart, gtm_view_cart -> view_cart, gtm_begin_checkout -> begin_checkout, gtm_purchase -> purchase.';

// Error
$_['error_permission'] = 'Внимание: нямате права за промяна на това разширение!';
$_['error_gtm_id_required'] = 'GTM Container ID е задължително, когато разширението е включено.';
$_['error_gtm_id_invalid'] = 'Невалидно GTM Container ID. Очакван формат: GTM-XXXXXXX.';
