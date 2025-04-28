from django import forms
from .models import Book, UserBook

class BookSearchForm(forms.Form):
    """Form for searching books"""
    query = forms.CharField(
        label="Search",
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Search by title, author, or ISBN'})
    )

class ImportBookForm(forms.Form):
    """Form for importing books from OpenLibrary"""
    isbn = forms.CharField(
        label="ISBN",
        required=False, 
        max_length=13,
        widget=forms.TextInput(attrs={'placeholder': 'Enter ISBN'})
    )
    ol_work_key = forms.CharField(
        label="OpenLibrary Work Key",
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Example: OL1234567W'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        isbn = cleaned_data.get('isbn')
        ol_work_key = cleaned_data.get('ol_work_key')
        
        if not isbn and not ol_work_key:
            raise forms.ValidationError("Please provide either ISBN or OpenLibrary Work Key")
            
        return cleaned_data

class UserBookForm(forms.ModelForm):
    """Form for tracking user's interactions with books"""
    class Meta:
        model = UserBook
        fields = ['status', 'rating', 'review', 'acquired_date', 'read_date']
        widgets = {
            'acquired_date': forms.DateInput(attrs={'type': 'date'}),
            'read_date': forms.DateInput(attrs={'type': 'date'}),
            'review': forms.Textarea(attrs={'rows': 3}),
        }
