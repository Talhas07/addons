/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useOpenMany2XRecord } from "@web/views/fields/relational_utils";
import { sprintf } from "@web/core/utils/strings";

import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { TagsList } from "@web/views/fields/many2many_tags/tags_list";

const { onMounted, onWillUpdateProps } = owl;

export class FieldMany2ManyTagsMobileTagsList extends TagsList {}
FieldMany2ManyTagsMobileTagsList.template = "FieldMany2ManyTagsMobileTagsList";


export class FieldMany2ManyTagsMobile extends Many2ManyTagsField {
    setup() {
        super.setup();

        this.openedDialogs = 0;
        this.recordsIdsToAdd = [];
        this.openMany2xRecord = useOpenMany2XRecord({
            resModel: this.props.relation,
            activeActions: {
                create: false,
                createEdit: false,
                write: true,
            },
            isToMany: true,
            onRecordSaved: async (record) => {
                if (record.data.mobile) {
                    this.recordsIdsToAdd.push(record.resId);
                }
            },
            fieldString: this.props.string,
        });

        // Using onWillStart causes an infinite loop, onMounted will handle the initial
        // check and onWillUpdateProps handles any addition to the field.
        onMounted(this.checkMobiles.bind(this, this.props));
        onWillUpdateProps(this.checkMobiles.bind(this));
    }

    async checkMobiles(props) {
        const invalidRecords = props.value.records.filter((record) => !record.data.mobile || !record.data.country_id);
        // Remove records with invalid data, open form view to edit those and readd them if they are updated correctly.
        const dialogDefs = [];
        for (const record of invalidRecords) {
            dialogDefs.push(this.openMany2xRecord({
                resId: record.resId,
                context: props.record.getFieldContext(this.props.name),
                title: sprintf(this.env._t("Edit: %s"), record.data.display_name),
            }));
        }
        this.openedDialogs += invalidRecords.length;
        const invalidRecordIds = invalidRecords.map(rec => rec.resId);
        if (invalidRecordIds.length) {
            this.props.value.replaceWith(props.value.currentIds.filter(id => !invalidRecordIds.includes(id)));
        }
        return Promise.all(dialogDefs).then(() => {
            this.openedDialogs -= invalidRecords.length;
            if (this.openedDialogs || !this.recordsIdsToAdd.length) {
                return;
            }
            props.value.add(this.recordsIdsToAdd, { isM2M: true });
            this.recordsIdsToAdd = [];
        });
    }

    get tags() {
        // Add mobile to our tags
        const tags = super.tags;
        const mobileByResId = this.props.value.records.reduce((acc, record) => {
            acc[record.resId] = record.data.mobile;
            acc[record.countryId] = record.data.country_id;
            return acc;
        }, {});
        tags.forEach(tag => {
            tag.mobile = mobileByResId[tag.resId];
            tag.country_id = mobileByResId[tag.countryId];
        });
        return tags;
    }
};

FieldMany2ManyTagsMobile.components = {
    ...FieldMany2ManyTagsMobile.components,
    TagsList: FieldMany2ManyTagsMobileTagsList,
};

FieldMany2ManyTagsMobile.fieldsToFetch = Object.assign({},
    Many2ManyTagsField.fieldsToFetch,
    {mobile: {name: 'mobile', type: 'char'}, country_id: {name: 'country_id', type: 'many2one', relation: 'res.partner'}},
);

FieldMany2ManyTagsMobile.additionalClasses = ["o_field_many2many_tags"];

registry.category("fields").add("many2many_tags_mobile", FieldMany2ManyTagsMobile);
