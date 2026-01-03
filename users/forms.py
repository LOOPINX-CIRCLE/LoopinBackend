"""
Forms for custom admin workflows in the users app.
"""

from django import forms

from .models import HostLeadWhatsAppTemplate


class HostLeadWhatsAppForm(forms.Form):
    """
    Form used by admins to send WhatsApp messages to host leads.

    Template variable mapping (Twilio content template):
        - {{1}} is always the host lead's first name (auto-filled server-side)
        - {{2}} is a customizable message body managed by marketing/ops
    """

    template_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )
    whatsapp_message = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "id": "id_whatsapp_message",
            }
        ),
        required=True,
        label="Message (template slot #2)",
        help_text="This text is injected into template variable {{2}}. "
                  "Keep it conversational and aligned with the marketing guidelines."
    )

    def __init__(self, *args, **kwargs):
        self.templates_qs = kwargs.pop("templates_qs", HostLeadWhatsAppTemplate.objects.none())
        super().__init__(*args, **kwargs)

    def clean_template_id(self):
        template_id = self.cleaned_data.get("template_id")
        if not template_id:
            return None
        try:
            template = self.templates_qs.get(pk=template_id)
        except HostLeadWhatsAppTemplate.DoesNotExist:
            raise forms.ValidationError("Selected recommendation no longer exists. Refresh the page and try again.")
        self.cleaned_data["template"] = template
        return template.id

    def clean_whatsapp_message(self):
        message = self.cleaned_data["whatsapp_message"].strip()
        if not message:
            raise forms.ValidationError("Message cannot be empty.")
        return message

