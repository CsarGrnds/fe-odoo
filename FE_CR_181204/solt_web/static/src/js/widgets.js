odoo.define('solt_web.kanban_ext', function (require) {
    "use strict";

    var core = require('web.core');
    var session = require('web.session');
    var Model = require('web.Model');
    var kanban_widgets = require('web_kanban.widgets');
    var AbstractField = kanban_widgets.AbstractField;
    var fields_registry = kanban_widgets.registry;
    var GraphWidget = require('web.GraphWidget');

    var QWeb = core.qweb;
    var _t = core._t;


    GraphWidget.include({
        display_graph: function () {
            if (this.to_remove) {
                nv.utils.offWindowResize(this.to_remove);
            }
            this.$el.empty();
            if (!this.data.length) {
                this.$el.append(QWeb.render('GraphView.error', {
                    title: _t("No data to display"),
                    description: _t("No data available for this chart. " +
                        "Try to add some records, or make sure that " +
                        "there is no active filter in the search bar."),
                }));
            } else {
                var chart = this['display_' + this.mode]();
                if(chart){
                    chart.tooltip.chartContainer(this.$el[0]);
                }
            }
        }
    });

    var KanbanM2MTags = AbstractField.extend({
        template: 'KanbanM2MTags',
        init: function (parent, field, $node) {
            this._super(parent, field, $node);
            this.search_field = this.options.search_field || 'name';
            this.dataset = new Model(this.field.relation);
        },
        willStart: function () {
            var self = this;
            return this.dataset.call("search_read",
                [[['id', 'in', this.field.raw_value]], [this.search_field]]).then(function (res) {
                self.kanban_tags = res;
            });
        },
    });

    fields_registry.add('kanban_m2m_tags', KanbanM2MTags);

    session.on('module_loaded', this, function () {
        var range = odoo.__DEBUG__.services["summernote/core/range"];
        $.summernote.eventHandler.modules.editor.saveRange = function ($editable, thenCollapse) {
            $editable.data('range', range.create());
            if (thenCollapse) {
                range.create().collapse().select();
            }
        };
    });
});
