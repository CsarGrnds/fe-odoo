odoo.define('solt_web.form_common_ext', function (require) {
    "use strict";

    var core = require('web.core');
    var data = require('web.data');
    var common = require('web.form_common');
    var pyeval = require('web.pyeval');
    var form_relational = require('web.form_relational');
    var session = require('web.session');
    var utils = require('web.utils');
    var Widget = require('web.Widget');
    var View = require('web.View');
    var FormView = require('web.FormView');
    var form_widgets = require('web.form_widgets');
    var SearchView = require('web.SearchView');
    var AutoComplete = require('web.AutoComplete');
    var Model = require('web.DataModel');
    var list_widget_registry = core.list_widget_registry;
    var QWeb = core.qweb;
    var _t = core._t;

    View.include({
        do_switch_view: function() {
            this._super.apply(this, arguments);
            var view_manager = $(".oe-view-manager-content");
            if(view_manager.length > 0){
                view_manager[0].scrollIntoView();
                $("#oe_main_menu_navbar")[0].scrollIntoView();
            }
        }
    });

    FormView.include({
        _process_save: function (save_obj) {
            var self = this;
            var prepend_on_create = save_obj.prepend_on_create;
            var def_process_save = $.Deferred();
            try {
                var form_invalid = false,
                    values = {},
                    first_invalid_field = null,
                    readonly_values = {},
                    deferred = [];

                $.when.apply($, deferred).always(function () {

                    _.each(self.fields, function (f) {
                        if (!f.is_valid()) {
                            form_invalid = true;
                            if (!first_invalid_field) {
                                first_invalid_field = f;
                            }
                        } else if (f.name !== 'id' && (!self.datarecord.id || f._dirty_flag)) {
                            // Special case 'id' field, do not save this field
                            // on 'create' : save all non readonly fields
                            // on 'edit' : save non readonly modified fields
                            if (!f.get("readonly")) {
                                values[f.name] = f.get_value(true);
                            } else {
                                if (f.node.attrs.send === "1" || f.options.rosend === "1" || f.options.rosend === 1 ||
                                    f.options.rosend === true || f.options.rosend === "True") {
                                    values[f.name] = f.get_value(true);
                                } else {
                                    readonly_values[f.name] = f.get_value(true);
                                }
                            }
                        }

                    });

                    // Heuristic to assign a proper sequence number for new records that
                    // are added in a dataset containing other lines with existing sequence numbers
                    if (!self.datarecord.id && self.fields.sequence && !_.has(values, 'sequence') && !_.isEmpty(self.dataset.cache)) {
                        // Find current max or min sequence (editable top/bottom)
                        var current = _[prepend_on_create ? "min" : "max"](
                            _.map(self.dataset.cache, function (o) {
                                return o.values.sequence
                            })
                        );
                        values['sequence'] = prepend_on_create ? current - 1 : current + 1;
                    }
                    if (form_invalid) {
                        self.set({'display_invalid_fields': true});
                        first_invalid_field.focus();
                        self.on_invalid();
                        def_process_save.reject();
                    } else {
                        self.set({'display_invalid_fields': false});
                        var save_deferral;
                        if (!self.datarecord.id) {
                            // Creation save
                            save_deferral = self.dataset.create(values, {readonly_fields: readonly_values}).then(function (r) {
                                return self.record_created(r, prepend_on_create);
                            }, null);
                        } else if (_.isEmpty(values)) {
                            // Not dirty, noop save
                            save_deferral = $.Deferred().resolve({}).promise();
                        } else {
                            // Write save
                            save_deferral = self.dataset.write(self.datarecord.id, values, {readonly_fields: readonly_values}).then(function (r) {
                                return self.record_saved(r);
                            }, null);
                        }
                        save_deferral.then(function (result) {
                            def_process_save.resolve(result);
                        }).fail(function () {
                            def_process_save.reject();
                        });
                    }
                });
            } catch (e) {
                console.error(e);
                return def_process_save.reject();
            }
            return def_process_save;
        },
    });

    var FieldMany2One = core.form_widget_registry.get('many2one');

    FieldMany2One.include({
        get_search_blacklist: function () {
            var blacklist = [];
            var self = this;
            var enable = ('unique_select' in self.node.attrs) ? JSON.parse(self.node.attrs['unique_select']) : false;
            if (self.field_manager && self.field_manager.dataset && self.field_manager.dataset.cache && enable) {
                var records = _.filter(self.field_manager.dataset.cache, function (o) {
                    var id = o.values[self.name]
                    if (id instanceof Array)
                        id = id[0];
                    return !(self.name in self.field_manager.datarecord) || id !== self.field_manager.datarecord[self.name][0]
                });
                blacklist = _.map(records, function (o) {
                    var id = o.values[self.name]
                    if (id instanceof Array)
                        id = id[0];
                    return id;
                })
            }
            return blacklist;
        },
        initialize_field: function () {
            this.is_started = true;
            core.bus.on('click', this, function () {
                if (!this.get("effective_readonly") && this.$input && this.$input.autocomplete('widget') && this.$input.autocomplete('widget').is(':visible')) {
                    this.$input.autocomplete("close");
                }
            });
            common.ReinitializeFieldMixin.initialize_field.call(this);
        },
        _quick_create: function() {
            this.ignore_focusout = true;
            this.no_ed = true;
            this.ed_def.reject();
//            this.ignore_focusout = false;
            return common.CompletionFieldMixin._quick_create.apply(this, arguments);
        }
    });

    var FieldPercent = form_widgets.FieldFloat.extend({
        template: "FieldPercent",
        widget_class: 'oe_form_field_float oe_form_field_percent',
        init: function () {
            this._super.apply(this, arguments);
        },
        start: function () {
            return this._super();
        }

    });
    var ColumnChar = list_widget_registry.get('field.char');

    var ColumnPercent = ColumnChar.extend({
        _format: function (row_data, options) {
            var value = row_data[this.id].value;
            if (value && this.password === 'True') {
                return this._super(row_data, options);
            }
            return value + ' %';
        }
    });

    core.list_widget_registry.add('field.percent', ColumnPercent);
    core.form_widget_registry.add('percent', FieldPercent);


    var ListView = core.view_registry.get('list');

    ListView.List.include({
        /** @lends instance.web.ListView.List#  update list_view_editable.js */
        row_clicked: function (event) {
            // same implementation
            if (!this.view.editable() || !this.view.is_action_enabled('edit')) {
                return this._super.apply(this, arguments);
            }

            var self = this;
            var args = arguments;
            var _super = self._super;

            var record_id = $(event.currentTarget).data('id');
            return this.view.start_edition(
                ((record_id) ? this.records.get(record_id) : null), {
                    focus_field: $(event.target).not(".oe_readonly").data('field'),
                }).fail(function () {
                // new code here
                if (self.view.editor.is_editing()) {
                    // to many clicks? the event is cancelled if already editing
                    // fail silently
                    // console.log(arguments[0])
                }
                else
                // end of new code
                    return _super.apply(self, args);
            });
        }
    });

    var FieldChar = core.form_widget_registry.get('char');

    FieldChar.include({
        // agregado la opcion de configurarle una expresion regular
        init: function () {
            this._super.apply(this, arguments);
            if (this.options.regex) {
                this.regex = new RegExp(this.options.regex);
            }
        },
        //-agregado la opcion de configurarle una mascara y las opciones de la mascara
        render_value: function () {
            this._super();
            if (this.options.mask) {
                this.$el.find('input').mask(this.options.mask, this.options.mask_options);
            }
        },
        is_valid: function () {
            var valid = this._super.apply(this, arguments);
            var value = this.get_value();
            if (valid === true && !this.get("invisible") && value) {
                if (this.regex) {
                    valid = this.regex.test(value);
                }
                if (this.field.size && value.length > this.field.size) {
                    valid = false;
                }
            }
            return valid;
        }
    });

    var FieldFloat = core.form_widget_registry.get('float');

    FieldFloat.include({
        //-agregado mascaras por defecto a los campos numericos
        init: function () {
            this._super.apply(this, arguments);
            if (!this.options.mask) {
                var l10n = _t.database.parameters;
                this.options.mask_options = {
                    translation: {
                        '.': {pattern: /[\.]/, optional: true},
                        ',': {pattern: /[,]/, optional: true}
                    }
                };
                this.options.mask_options.translation[l10n.decimal_point].recursive = true;
                if (this.field.type == 'integer') {
                    if (this.field.size < 9) {
                        this.options.mask = "9"
                        for (i = 0; i < this.field.size - 1; i++) {
                            if (i % 3 == 0)
                                this.options.mask += l10n.thousands_sep;
                            this.options.mask += "9";
                        }
                        this.options.mask = this.options.mask.split("").reverse().join("");
                    } else
                        this.options.mask = "9" + l10n.thousands_sep + "999" + l10n.thousands_sep + "999" + l10n.thousands_sep + "999";
                }
                else if (this.field.type == 'integer_big') {
                    if (this.field.size < 18) {
                        this.options.mask = "9";
                        for (var i = 0; i < this.field.size - 1; i++) {
                            if (i % 3 == 0)
                                this.options.mask += l10n.thousands_sep;
                            this.options.mask += "9";
                        }
                        this.options.mask = this.options.mask.split("").reverse().join("");
                    } else
                        this.options.mask = "9" + l10n.thousands_sep + "999" + l10n.thousands_sep + "999" + l10n.thousands_sep + "999" + l10n.thousands_sep + "999" + l10n.thousands_sep + "999" + l10n.thousands_sep + "999";
                }
                else if (this.field.type == 'float') {
                    if (this.widget == 'float_time') {
                        this.options.mask = "00:50";
                        this.options.mask_options = {translation: {'5': {pattern: /[0-5]/}}};
                    } else {
                        var dec = "0";
                        var j = (this.digits ? this.digits[1] : 2);
                        for (i = 1; i < j; i++)
                            dec += "0";
                        j = (this.digits ? this.digits[0] : 16);
                        var dig = "9";
                        for (i = 1; i < j; i++) {
                            if (i % 3 == 0)
                                dig += l10n.thousands_sep;
                            dig += "9";
                        }
                        dig = dig.split("").reverse().join("");
                        this.options.mask = dig + l10n.decimal_point + dec;
                        this.options.mask_options.maxlength = false;
                    }
                }
                this.options.mask_options.negative = true;
            }
        },
        //-END-
        // -Validando tamanho de campos numericos (integer, integer_big, float)
        is_valid: function () {
            var is_valid = this._super.apply(this, arguments);
            var value = this.get_value();
            if (is_valid && !this.get("invisible") && value) {
                if (this.field.type == 'integer' && (value > 2147483647 || value < -2147483648)) {
                    is_valid = false;
                }
                else if (this.field.type == 'integer_big' && (value > 9223372036854775807 || value < -9223372036854775808)) {
                    is_valid = false;
                }
            }
            return is_valid;
        }
        //-END-
    });

    var FieldEmail = core.form_widget_registry.get('email');

    FieldEmail.include({
        init: function () {
            this._super.apply(this, arguments);
            if (!this.regex) {
                this.regex = new RegExp("^(\\w+(\\.\\w+)*(\\-\\w+)*(\\_\\w+)*@\\w+(\\_\\w+)*(\\-\\w+)*(\\w+\\.)+[a-z]+[ ]?)+$");
            }
        }
    });

    var FieldSelection = core.form_widget_registry.get('selection');

    var FieldIconList = FieldSelection.extend({
        template: 'FieldIconList',
        init: function (field_manager, node) {
            var self = this;
            this._super(field_manager, node);
            var modules = self.node.attrs.modules
            if (modules === undefined)
                modules = 'web';
            self.rpc('/web/webclient/imglist', {mods: modules}, {async: false}).done(function (files) {
                self.values = _(files).chain()
                    .reject(function (v) {
                        return v[0] === false && v[1] === '';
                    })
                    .unshift([false, ''])
                    .value();
            });
        },
        store_dom_value: function () {
            if (!this.get('effective_readonly') && this.$('select').length) {
                this.internal_set_value(
                    this.values[this.$('select')[0].selectedIndex][0]);
                this.render_icon();
            }
        },
        render_icon: function () {
            var self = this;
            var option = _(this.values).detect(function (record) {
                return record[0] === self.get('value');
            });
            this.$('img')[0].src = "";
            if (option && option[0])
                this.$('img')[0].src = option[0];
        },
        render_value: function () {
            if (!this.get("effective_readonly")) {
                var index = 0;
                for (var i = 0, ii = this.values.length; i < ii; i++) {
                    if (this.values[i][0] === this.get('value')) index = i;
                }
                this.$el.find('select')[0].selectedIndex = index;
            }
            this.render_icon();
        },
        set_dimensions: function (height, width) {

        }
    });

    core.form_widget_registry.add('icon', FieldIconList);

    function facet_from(field, pair) {
        return {
            field: field,
            category: field.attrs.string,
            values: [{label: pair[1], value: pair[0]}]
        };
    }

    var ManyToOneField = core.search_widgets_registry.get('many2one');

    ManyToOneField.include({
        complete: function (value) {
            if (_.isEmpty(value)) {
                return $.when(null);
            }
            var label = _.str.sprintf(_.str.escapeHTML(
                _t("Search %(field)s for: %(value)s")), {
                field: '<em>' + _.escape(this.attrs.string) + '</em>',
                value: '<strong>' + _.escape(value) + '</strong>'
            });
            this.facet = new SearchView.Facet({
                category: this.attrs.string,
                field: this,
                values: [{label: value, value: value, operator: 'ilike'}]
            }, {});
            return $.when([{
                label: label,
                facet: this.facet,
                expand: this.expand.bind(this),
            }]);
        },
        expand: function (needle) {
            var self = this;
            // FIXME: "concurrent" searches (multiple requests, mis-ordered responses)
            var context = pyeval.eval(
                'contexts', [self.searchview.dataset.get_context(), self.get_context(this.facet)]);
            var args = this.attrs.domain;
            if (typeof args === 'string') {
                try {
                    args = pyeval.eval('domain', args);
                } catch (e) {
                    args = [];
                }
            }
            return this.model.call('name_search', [], {
                name: needle,
                args: args,
                limit: 8,
                context: context
            }).then(function (results) {
                if (_.isEmpty(results)) {
                    return null;
                }
                return _(results).map(function (result) {
                    return {
                        label: _.escape(result[1]),
                        facet: facet_from(self, result)
                    };
                });
            });
        },
    });

    AutoComplete.include({
        render_search_results: function (results) {
            var self = this;
            var $list = this.$('ul');
            $list.empty();
            var render_separator = false;
            results.forEach(function (result) {
                if (result.is_separator) {
                    if (render_separator)
                        $list.append($('<li>').addClass('oe-separator'));
                    render_separator = false;
                } else {
                    var $item = self.make_list_item(result).appendTo($list);
                    result.$el = $item;
                    render_separator = true;
                    if (result.expand) {
                        self.current_result = $item.data('result');
                        self.expand();
                    }
                }
            });
            this.show();
        },
        expand: function() {
            var self = this;
            var current_result = this.current_result;
            current_result.expand(this.get_search_string().trim()).then(function(results) {
                (results || [{
                    label: '(no result)'
                }]).reverse().forEach(function(result) {
                    result.indent = true;
                    var $li = self.make_list_item(result);
                    current_result.$el.after($li);
                });
                current_result.expanded = true;
                current_result.$el.find('span.oe-expand').html('▼');
            });
        },
    });

    core.form_widget_registry.get('image').include({
        init: function(field_manager, node) {
            var self = this;
            this._super(field_manager, node);
            new Model('ir.config_parameter').call('get_param', ['settings.attachment.max_upload_size']).then(function(max_upload_size) {
                if(max_upload_size){
                    self.max_upload_size = parseInt(max_upload_size)
                }
            });
        }
    });

    core.form_widget_registry.get('binary').include({
        init: function(field_manager, node) {
            var self = this;
            this._super(field_manager, node);
            new Model('ir.config_parameter').call('get_param', ['settings.attachment.max_upload_size']).then(function(max_upload_size) {
                if(max_upload_size){
                    self.max_upload_size = parseInt(max_upload_size)
                }
            });
        }
    });
});
