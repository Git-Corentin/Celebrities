from django import forms
from .models import Celebrity
from .models import Activity
from django.core import validators
from .models import CelebritySighting
from django.forms.widgets import FileInput

class CustomDateInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, **kwargs):
        kwargs['format'] = '%Y-%m-%d'
        super().__init__(**kwargs)
class CelebrityForm(forms.ModelForm):
    activities = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"id": "activity-search", "placeholder": "Recherchez une activité..."}),
        validators = [validators.MinLengthValidator(1)]
    )

    image = forms.ImageField(required=False, widget=FileInput)

    class Meta:
        model = Celebrity
        fields = ['name', 'image']

class CelebritySightingForm(forms.ModelForm):
    class Meta:
        model = CelebritySighting
        fields = ['date_seen', 'location', 'notes']
        widgets = {
            'date_seen': CustomDateInput(),
        }
class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["name"]
