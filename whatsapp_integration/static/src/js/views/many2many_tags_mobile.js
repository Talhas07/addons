/* @odoo-module */

import { onMounted } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { TagsList } from "@web/core/tags_list/tags_list";
import { sprintf } from "@web/core/utils/strings";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { useOpenMany2XRecord } from "@web/views/fields/relational_utils";

export class FieldMany2ManyTagsMobileTagsList extends TagsList {}
FieldMany2ManyTagsMobileTagsList.template = "FieldMany2ManyTagsMobileTagsList";

export class FieldMany2ManyTagsMobile extends Many2ManyTagsField {
    static props = {
        ...Many2ManyTagsField.props,
        context: { type: Object, optional: true },
    };

    setup() {
        super.setup();

        this.openedDialogs = 0;
        this.recordsIdsToAdd = [];
        this.openMany2xRecord = useOpenMany2XRecord({
            resModel: this.relation,
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

        const update = this.update;
        this.update = async (object) => {
            await update(object);
            await this.checkMobiles();
        };

        onMounted(() => {
            this.checkMobiles();
        });
    }

    async checkMobiles() {
        const list = this.props.record.data[this.props.name];
        const invalidRecords = list.records.filter((record) => !record.data.mobile || !record.data.country_id);
        // Remove records with invalid data, open form view to edit those and readd them if they are updated correctly.
        const dialogDefs = [];
        for (const record of invalidRecords) {
            dialogDefs.push(
                this.openMany2xRecord({
                    resId: record.resId,
                    context: this.props.context,
                    title: sprintf(_t("Edit: %s"), record.data.display_name),
                })
            );
        }
        this.openedDialogs += invalidRecords.length;
        await Promise.all(dialogDefs);

        this.openedDialogs -= invalidRecords.length;
        if (this.openedDialogs || !this.recordsIdsToAdd.length) {
            return;
        }

        const invalidRecordIds = invalidRecords.map((rec) => rec.resId);
        await list.addAndRemove({
            remove: invalidRecordIds.filter((id) => !this.recordsIdsToAdd.includes(id)),
            reload: true,
        });
        this.recordsIdsToAdd = [];
    }

    get tags() {
        // Add mobile to our tags
        const tags = super.tags;
        const mobileByResId = this.props.record.data[this.props.name].records.reduce(
            (acc, record) => {
                acc[record.resId] = record.data.mobile;
                acc[record.countryId] = record.data.country_id;
                return acc;
            },
            {}
        );
        tags.forEach(tag => {
            tag.mobile = mobileByResId[tag.resId];
            tag.country_id = mobileByResId[tag.countryId];
        });
        return tags;
    }
}

FieldMany2ManyTagsMobile.components = {
    ...FieldMany2ManyTagsMobile.components,
    TagsList: FieldMany2ManyTagsMobileTagsList,
};

export const fieldMany2ManyTagsMobile = {
    ...many2ManyTagsField,
    component: FieldMany2ManyTagsMobile,
    extractProps(fieldInfo, dynamicInfo) {
        const props = many2ManyTagsField.extractProps(...arguments);
        props.context = dynamicInfo.context;
        return props;
    },
    relatedFields: (fieldInfo) => {
        return [...many2ManyTagsField.relatedFields(fieldInfo), { name: "mobile", type: "char" }, {name: 'country_id', type: 'many2one', relation: 'res.partner'}];
    },
    additionalClasses: ["o_field_many2many_tags"],
};

registry.category("fields").add("many2many_tags_mobile", fieldMany2ManyTagsMobile);
