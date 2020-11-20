from django import forms
from .models import dataset, model

class SetForm(forms.ModelForm):
    class Meta:
        model = dataset
        exclude = ('user','size', 'budget')
class ModelForm(forms.ModelForm):
    class Meta:
        model = model
        exclude = ('user',)