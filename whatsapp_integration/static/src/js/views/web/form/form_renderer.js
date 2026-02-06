/* @odoo-module */

import { onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(this.onMounted);
        onWillUnmount(this.onWillUnmount);
        this.formRootRef = useRef("compiled_view_root");
        this.qr_timer = 0;
        this.orm = useService("orm");
    },
   
    onMounted() {
        if (this.formRootRef && this.formRootRef.el) {
            const formViewElement = this.formRootRef.el.closest('.o_form_view');
            if (formViewElement && formViewElement.classList.contains('qr_code_form')) {
                if (this.env.config.viewArch.className == 'qr_code_form') {
                    formViewElement.querySelector('.qr_img').src = this.env.searchModel.context.qr_image;
                }
                const resID = this.props.record && this.props.record.evalContext.context && this.props.record.evalContext.context.wiz_id;
                if (resID) {
                    this.qr_timer = setInterval(async () => {
                        try {
                            const res = await this.orm.call('whatsapp.msg', 'get_qr_img', [resID]);
                            if (res) {
                                this.formRootRef.el.querySelector('img.qr_img').src = res;
                            }
                        } catch (err) {
                            console.error(err);
                        }
                    }, 9000);
                }
                const sendBtn = this.formRootRef.el.querySelector('button.send_btn');
                if (sendBtn) {
                    sendBtn.addEventListener('click', () => {
                        clearInterval(this.qr_timer);
                    });
                }
                const closeBtn = this.formRootRef.el.querySelector('button.close_btn');
                if (closeBtn) {
                    closeBtn.addEventListener('click', () => {
                        clearInterval(this.qr_timer);
                    });
                }
            }
        }
    },
    onWillUnmount() {
        if (this.formRootRef && this.formRootRef.el) {
            const formViewElement = this.formRootRef.el.closest('.o_form_view');
            if (formViewElement && formViewElement.classList.contains('qr_code_form') && this.qr_timer) {
                clearInterval(this.qr_timer);
            }
        }
    },
});
