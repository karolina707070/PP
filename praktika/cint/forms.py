from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Request, Comment, Assessment, User, Role



class CustomUserCreationForm(UserCreationForm):
    phone = forms.CharField(max_length=20, required=False, label='Телефон')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'password1', 'password2', 'phone')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()

        client_role, _ = Role.objects.get_or_create(name='Клиент')
        user.role = client_role
        user.save()
        return user


class RequestCreateForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['title', 'goal', 'expected_results', 'description',
                  'deadline', 'budget', 'direction', 'image']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'goal': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'expected_results': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in self.fields:
            if field_name not in ['goal', 'expected_results', 'description']:
                self.fields[field_name].widget.attrs.update({'class': 'form-control'})

        for field_name in ['title', 'goal', 'expected_results', 'description', 'direction']:
            self.fields[field_name].required = True

    def clean_budget(self):
        budget = self.cleaned_data.get('budget')
        if budget is not None and budget <= 0:
            raise forms.ValidationError('Бюджет должен быть положительным числом.')
        return budget


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {'text': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Ваш комментарий...', 'class': 'form-control'})}
        labels = {'text': ''}


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ['labor_hours', 'resources', 'conclusion']
        widgets = {
            'resources': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'conclusion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'labor_hours': forms.NumberInput(attrs={'class': 'form-control'}),
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
        empty_label="Не назначен",
        widget=forms.Select(attrs={'class': 'form-select'})
    )