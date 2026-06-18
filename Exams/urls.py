from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    # Authentication
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),
    # Teacher
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/exam/create/', views.create_exam, name='create_exam'),
    path('teacher/exam/<uuid:exam_uid>/question/add/', views.add_question, name='add_question'),
    path('teacher/exam/<uuid:exam_uid>/edit/', views.edit_exam, name='edit_exam'),
    path('teacher/question/<uuid:question_uid>/edit/', views.edit_question, name='edit_question'),
    path('teacher/exam/<uuid:exam_uid>/analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('teacher/exam/<uuid:exam_uid>/export/', views.export_results_csv, name='export_results_csv'),
    # Student
    path('student/exam/', views.student_exam_access, name='student_exam_access'),
    path('quiz/', views.quiz, name='quiz'),
    path('quiz/data/', views.get_quiz, name='get_quiz'),
    path('quiz/submit/', views.submit_quiz, name='submit_quiz'),
    # AI Proctoring
    path('quiz/proctor/log/', views.log_proctoring_event, name='log_proctoring_event'),
    # LMS Integration
    path('api/lms/<uuid:exam_uid>/grades/', views.lms_grade_sync, name='lms_grade_sync'),
]
