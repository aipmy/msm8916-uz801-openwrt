'use strict';
'require baseclass';
'require form';

return baseclass.extend({
	trigger: _('SIM Card inserted (kernel: simcard)'),
	description: _('The LED lights up when a physical SIM card is inserted and detected.'),
	kernel: true,
	addFormOptions: function(s) {
		var o;
		o = s.option(form.Flag, 'inverted', _('Invert LED state'), _('When inverted, the LED is lit when SIM is missing and turns OFF when SIM is inserted.'));
		o.rmempty = true;
		o.modalonly = true;
		o.depends('trigger', 'simcard');
	}
});
