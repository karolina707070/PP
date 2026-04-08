from django import forms
from .models import Request, Comment, Assessment, User

class RequestCreateForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['title', 'goal', 'expected_results', 'description',
                  'deadline', 'budget', 'direction', 'image']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'goal': forms.Textarea(attrs={'rows': 3}),
            'expected_results': forms.Textarea(attrs={'rows': 3}),
            'description': forms.Textarea(attrs={'rows': 5}),
        }
        labels = {
            'title': 'Название проекта',
            'goal': 'Цель',
            'expected_results': 'Ожидаемые результаты',
            'description': 'Описание',
            'deadline': 'Желаемый срок',
            'budget': 'Бюджет',
            'direction': 'Направление',
            'image': 'Изображение',
        }

    def clean_budget(self):
        budget = self.cleaned_data.get('budget')
        if budget is not None and budget <= 0:
            raise forms.ValidationError('Бюджет должен быть положительным числом.')
        return budget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['title', 'goal', 'expected_results', 'description', 'direction']:
            self.fields[field_name].required = True

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {'text': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Ваш комментарий...'})}
        labels = {'text': ''}

class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ['labor_hours', 'resources', 'conclusion']
        widgets = {
            'resources': forms.Textarea(attrs={'rows': 3}),
            'conclusion': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'labor_hours': 'Трудозатраты (часы)',
            'resources': 'Необходимые ресурсы',
            'conclusion': 'Заключение',
        }

class AssignSpecialistForm(forms.Form):
    specialist = forms.ModelChoiceField(
        queryset=User.objects.filter(role__name='Специалист'),
        label='Назначить специалиста',
        required=False,
        empty_label="Не назначен"
    )