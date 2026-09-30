<?php
// Heading
$_['heading_title'] = 'Google Tag Manager + GA4 Ecommerce';

// Text
$_['text_extension'] = 'Extensions';
$_['text_success'] = 'Success: You have modified Google Tag Manager + GA4 Ecommerce settings!';
$_['text_edit'] = 'Edit Google Tag Manager + GA4 Ecommerce';
$_['text_default'] = 'Default';
$_['text_general'] = 'General';
$_['text_ecommerce'] = 'Ecommerce dataLayer';
$_['text_information'] = 'This extension uses OpenCart Events and does not modify core or theme files. Ecommerce pushes use generic event names plus a ga4_event field.';
$_['text_duplicate'] = 'Duplicate protection: if another standard GTM loader is already present in the rendered header, this extension will not inject a second GTM loader. Ecommerce dataLayer events will still be pushed.';
$_['text_consent'] = 'Consent note: this version does not set or override Consent Mode. Keep consent management in your CMP / cookie-consent solution.';
$_['text_event_mapping'] = 'Event mapping';

// Entry
$_['entry_store'] = 'Store';
$_['entry_status'] = 'Status';
$_['entry_gtm_id'] = 'GTM Container ID';
$_['entry_ecommerce_status'] = 'Ecommerce tracking';
$_['entry_view_item'] = 'View item';
$_['entry_add_to_cart'] = 'Add to cart';
$_['entry_remove_from_cart'] = 'Remove from cart';
$_['entry_view_cart'] = 'View cart';
$_['entry_begin_checkout'] = 'Begin checkout';
$_['entry_purchase'] = 'Purchase';

// Help
$_['help_store'] = 'Each store can use a different GTM Container ID and independent tracking settings.';
$_['help_gtm_id'] = 'Example: GTM-ABC1234. The ID is stored per OpenCart store.';
$_['help_ecommerce'] = 'Pushes ecommerce data into window.dataLayer. Google Analytics itself is configured in Google Tag Manager.';
$_['help_event_mapping'] = 'Generic event -> ga4_event: gtm_view_item -> view_item, gtm_add_to_cart -> add_to_cart, gtm_remove_from_cart -> remove_from_cart, gtm_view_cart -> view_cart, gtm_begin_checkout -> begin_checkout, gtm_purchase -> purchase.';

// Error
$_['error_permission'] = 'Warning: You do not have permission to modify this extension!';
$_['error_gtm_id_required'] = 'GTM Container ID is required when the extension is enabled.';
$_['error_gtm_id_invalid'] = 'Invalid GTM Container ID. Expected format: GTM-XXXXXXX.';
