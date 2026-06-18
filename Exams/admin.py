from django.contrib import admin
from .models import Exam, Question, Answer, StudentAttempt

# admin.site.register(Category)

class AnswerAdmin(admin.StackedInline):
    model = Answer
    
class QuestionAdmin(admin.ModelAdmin):
    inlines = [AnswerAdmin]

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['name', 'exam_key', 'teacher', 'category', 'is_active', 'created_at']
    search_fields = ['name', 'exam_key', 'teacher__username']
    list_filter = ['is_active', 'category', 'created_at']


admin.site.register(Question , QuestionAdmin)
admin.site.register(Answer)
admin.site.register(StudentAttempt)
