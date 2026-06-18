from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from .models import Exam, Question, Answer, StudentAttempt, ProctoringEvent
import json
import csv
import random
from django.utils import timezone
from django.db.models import Avg, Sum, Count, Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from Category.models import Category



#  HOME

def home(request):
    return render(request, 'home.html')


#  AUTH: Login, Register, Logout
def login(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)

        if user is not None:
            auth_login(request, user)
            messages.success(request, 'Welcome back.')
            return redirect('teacher_dashboard')

        messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html')


def register(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('register')

        if User.objects.filter(username=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return redirect('login')

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        auth_login(request, user)
        messages.success(request, 'Your account has been created.')
        return redirect('teacher_dashboard')

    return render(request, 'register.html')


def logout(request):
    auth_logout(request)
    messages.success(request, 'You have been signed out.')
    return redirect('home')


#  TEACHER DASHBOARD
@login_required(login_url='login')
def teacher_dashboard(request):
    exams = Exam.objects.filter(teacher=request.user).order_by('-created_at')
    categories = Category.objects.all().order_by('name')

    # ── Real-Time Analytics summary ──
    total_exams = exams.count()
    total_students = StudentAttempt.objects.filter(exam__teacher=request.user).count()
    total_questions = Question.objects.filter(exam__teacher=request.user).count()
    avg_pass_rate = 0
    if total_students > 0:
        submitted = StudentAttempt.objects.filter(exam__teacher=request.user, total_marks__gt=0)
        if submitted.exists():
            passed = sum(1 for a in submitted if a.percentage >= 40)
            avg_pass_rate = round((passed / submitted.count()) * 100, 1)

    return render(request, 'teacher/teacher_dashboard.html', {
        'exams': exams,
        'categories': categories,
        'total_exams': total_exams,
        'total_students': total_students,
        'total_questions': total_questions,
        'avg_pass_rate': avg_pass_rate,
    })


#  CREATE EXAM  (+ Proctoring, Security, LMS, Timer)
@login_required(login_url='login')
@require_POST
def create_exam(request):
    name = request.POST.get('name', '').strip()
    category_id = request.POST.get('category')
    category_name = request.POST.get('category_name', '').strip()

    if not name:
        messages.error(request, 'Exam name is required.')
        return redirect('teacher_dashboard')

    if category_id:
        category = get_object_or_404(Category, id=category_id)
    elif category_name:
        category, _ = Category.objects.get_or_create(name=category_name)
    else:
        messages.error(request, 'Please select or create a category.')
        return redirect('teacher_dashboard')

    # ── Feature toggles from form ──
    proctoring_enabled = request.POST.get('proctoring_enabled') == 'on'
    browser_lockdown = request.POST.get('browser_lockdown') == 'on'
    shuffle_questions = request.POST.get('shuffle_questions', 'on') == 'on'
    lms_platform = request.POST.get('lms_platform', 'none')
    lms_course_id = request.POST.get('lms_course_id', '').strip()

    try:
        time_limit = int(request.POST.get('time_limit_minutes', 0) or 0)
    except ValueError:
        time_limit = 0

    try:
        max_questions = int(request.POST.get('max_questions', 0) or 0)
    except ValueError:
        max_questions = 0

    exam = Exam.objects.create(
        name=name,
        category=category,
        teacher=request.user,
        proctoring_enabled=proctoring_enabled,
        browser_lockdown=browser_lockdown,
        shuffle_questions=shuffle_questions,
        time_limit_minutes=time_limit,
        max_questions=max_questions,
        lms_platform=lms_platform,
        lms_course_id=lms_course_id,
    )
    messages.success(request, f'Exam created. Key: {exam.exam_key}')
    return redirect('teacher_dashboard')


#  ADD QUESTION  (Smart Question Bank: difficulty + tags)
@login_required(login_url='login')
@require_POST
def add_question(request, exam_uid):
    exam = get_object_or_404(Exam, uid=exam_uid, teacher=request.user)
    question_text = request.POST.get('question', '').strip()
    marks = request.POST.get('marks', '1')
    answers = [
        request.POST.get('answer_1', '').strip(),
        request.POST.get('answer_2', '').strip(),
        request.POST.get('answer_3', '').strip(),
        request.POST.get('answer_4', '').strip(),
    ]
    correct_index = request.POST.get('correct_answer')

    # ── Smart Question Bank ──
    difficulty = request.POST.get('difficulty', 'medium')
    tags = request.POST.get('tags', '').strip()

    if not question_text or not correct_index or not any(answers):
        messages.error(request, 'Question, answers, and correct option are required.')
        return redirect('teacher_dashboard')

    if correct_index not in ['1', '2', '3', '4'] or not answers[int(correct_index) - 1]:
        messages.error(request, 'Selected correct option must have answer text.')
        return redirect('teacher_dashboard')

    try:
        marks_value = max(int(marks or 1), 1)
    except ValueError:
        marks_value = 1

    question = Question.objects.create(
        exam=exam,
        category=exam.category,
        question=question_text,
        marks=marks_value,
        difficulty=difficulty,
        tags=tags,
    )

    for index, answer_text in enumerate(answers, start=1):
        if answer_text:
            Answer.objects.create(
                question=question,
                answer=answer_text,
                is_correct=str(index) == correct_index,
            )

    messages.success(request, 'Question added.')
    return redirect('teacher_dashboard')


#  EDIT EXAM
@login_required(login_url='login')
def edit_exam(request, exam_uid):
    exam = get_object_or_404(Exam, uid=exam_uid, teacher=request.user)
    if request.method == 'POST':
        exam.name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        category_name = request.POST.get('category_name', '').strip()
        
        if category_id:
            exam.category = get_object_or_404(Category, id=category_id)
        elif category_name:
            exam.category, _ = Category.objects.get_or_create(name=category_name)
            
        exam.proctoring_enabled = request.POST.get('proctoring_enabled') == 'on'
        exam.browser_lockdown = request.POST.get('browser_lockdown') == 'on'
        exam.shuffle_questions = request.POST.get('shuffle_questions') == 'on'
        exam.lms_platform = request.POST.get('lms_platform', 'none')
        exam.lms_course_id = request.POST.get('lms_course_id', '').strip()
        
        try:
            exam.time_limit_minutes = int(request.POST.get('time_limit_minutes', 0) or 0)
        except ValueError:
            pass
            
        try:
            exam.max_questions = int(request.POST.get('max_questions', 0) or 0)
        except ValueError:
            pass
            
        exam.save()
        messages.success(request, 'Exam updated successfully.')
        return redirect('teacher_dashboard')
        
    categories = Category.objects.all().order_by('name')
    return render(request, 'teacher/tredit_exam.html', {'exam': exam, 'categories': categories})



#  EDIT QUESTION
@login_required(login_url='login')
def edit_question(request, question_uid):
    question = get_object_or_404(Question, uid=question_uid, exam__teacher=request.user)
    answers = list(Answer.objects.filter(question=question).order_by('created_at'))
    
    if request.method == 'POST':
        question.question = request.POST.get('question', '').strip()
        
        try:
            question.marks = max(int(request.POST.get('marks', 1) or 1), 1)
        except ValueError:
            pass
            
        question.difficulty = request.POST.get('difficulty', 'medium')
        question.tags = request.POST.get('tags', '').strip()
        question.save()
        
        correct_index = request.POST.get('correct_answer')
        submitted_answers = [
            request.POST.get('answer_1', '').strip(),
            request.POST.get('answer_2', '').strip(),
            request.POST.get('answer_3', '').strip(),
            request.POST.get('answer_4', '').strip(),
        ]
        
        for i, ans_obj in enumerate(answers):
            if i < len(submitted_answers) and submitted_answers[i]:
                ans_obj.answer = submitted_answers[i]
                ans_obj.is_correct = str(i + 1) == correct_index
                ans_obj.save()
                
        messages.success(request, 'Question updated successfully.')
        return redirect('teacher_dashboard')
        
    return render(request, 'teacher/tedit_question.html', {'question': question, 'answers': answers})


#  STUDENT EXAM ACCESS
def student_exam_access(request):
    exam_key = request.GET.get('key', '').strip()

    if request.method == 'POST':
        exam_key = request.POST.get('exam_key', '').strip()
        roll_no = request.POST.get('roll_no', '').strip()
        exam = Exam.objects.filter(exam_key=exam_key, is_active=True).first()

        if not exam:
            messages.error(request, 'Invalid or inactive exam key.')
            return redirect('student_exam_access')

        if not roll_no:
            messages.error(request, 'Roll number is required.')
            return redirect('student_exam_access')

        attempt, created = StudentAttempt.objects.get_or_create(exam=exam, roll_no=roll_no)
        if created or not attempt.is_submitted:
            attempt.started_at = timezone.now()
            attempt.save()
        elif attempt.is_submitted:
            messages.error(request, 'You have already submitted this exam.')
            return redirect('student_exam_access')

        return redirect(f'/quiz/?key={exam.exam_key}&roll={roll_no}')

    return render(request, 'student_access.html', {'exam_key': exam_key})


#  QUIZ PAGE
def quiz(request):
    exam_key = request.GET.get('key', '').strip()
    roll_no = request.GET.get('roll', '').strip()
    exam = Exam.objects.filter(exam_key=exam_key, is_active=True).first()

    if not exam or not roll_no:
        messages.error(request, 'Enter exam key and roll number to start.')
        return redirect('student_exam_access')

    return render(request, 'teacher/quiz.html', {
        'exam': exam,
        'roll_no': roll_no,
    })


#  GET QUIZ DATA  (Smart Question Bank shuffle/filter)
def get_quiz(request):
    try:
        exam_key = request.GET.get('key', '').strip()
        exam = get_object_or_404(Exam, exam_key=exam_key, is_active=True)
        quizs = Question.objects.filter(exam=exam)

        # ── Smart Question Bank: Category filter ──
        if request.GET.get('category'):
            quizs = quizs.filter(
                category__name__icontains=request.GET.get('category')
            )

        # ── Smart Question Bank: Difficulty filter ──
        if request.GET.get('difficulty'):
            quizs = quizs.filter(difficulty=request.GET.get('difficulty'))

        # ── Smart Question Bank: Tag filter ──
        if request.GET.get('tag'):
            quizs = quizs.filter(tags__icontains=request.GET.get('tag'))

        quizs = list(quizs)

        # ── Smart Question Bank: Auto-shuffle ──
        if exam.shuffle_questions:
            random.shuffle(quizs)

        # ── Smart Question Bank: Max questions limit ──
        limit = exam.max_questions if exam.max_questions > 0 else 10
        quizs = quizs[:limit]

        data = []
        for quiz in quizs:
            options = quiz.get_answers(include_correctness=False)
            random.shuffle(options)

            data.append({
                'uid': str(quiz.uid),
                'category': quiz.category.name if quiz.category else None,
                'question': quiz.question,
                'marks': quiz.marks,
                'difficulty': quiz.difficulty,
                'tags': quiz.get_tag_list(),
                'options': options,
            })

        payload = {
            'status': True,
            'exam': exam.name,
            'time_limit_minutes': exam.time_limit_minutes,
            'proctoring_enabled': exam.proctoring_enabled,
            'browser_lockdown': exam.browser_lockdown,
            'data': data
        }

        return JsonResponse(payload)

    except Exception as e:
        return JsonResponse({
            'status': False,
            'message': str(e)
        })


#  SUBMIT QUIZ  (Auto-Grading + Analytics tracking)
@require_POST
def submit_quiz(request):
    try:
        data = json.loads(request.body)
        exam_key = data.get('exam_key', '').strip()
        roll_no = data.get('roll_no', '').strip()
        submitted_answers = data.get('answers', {})
        time_taken = data.get('time_taken_seconds', 0)

        if not exam_key or not roll_no:
            return JsonResponse({
                'status': False,
                'message': 'Exam key and roll number are required.'
            })

        exam = get_object_or_404(Exam, exam_key=exam_key, is_active=True)
        attempt, _ = StudentAttempt.objects.get_or_create(exam=exam, roll_no=roll_no)

        # ── Auto-Grading: Score each question ──
        score = 0
        total_marks = 0
        question_results = []

        question_uids = list(submitted_answers.keys())
        questions = Question.objects.filter(exam=exam, uid__in=question_uids)

        for question in questions:
            total_marks += question.marks
            chosen_answer_uid = submitted_answers.get(str(question.uid))
            is_correct = False
            correct_answer = Answer.objects.filter(question=question, is_correct=True).first()

            if chosen_answer_uid:
                is_correct = Answer.objects.filter(
                    question=question,
                    uid=chosen_answer_uid,
                    is_correct=True
                ).exists()
                if is_correct:
                    score += question.marks

            question_results.append({
                'question': question.question,
                'marks': question.marks,
                'is_correct': is_correct,
                'earned': question.marks if is_correct else 0,
                'correct_answer': correct_answer.answer if correct_answer else '',
            })

        # ── Real-Time Analytics: Track timing ──
        attempt.score = score
        attempt.total_marks = total_marks
        attempt.finished_at = timezone.now()
        attempt.time_taken_seconds = int(time_taken) if time_taken else 0
        attempt.is_submitted = True
        attempt.save()

        return JsonResponse({
            'status': True,
            'score': score,
            'total_marks': total_marks,
            'percentage': attempt.percentage,
            'grade': attempt.grade,
            'question_results': question_results,
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'status': False,
            'message': 'Invalid JSON format.'
        })
    except Exception as e:
        return JsonResponse({
            'status': False,
            'message': str(e)
        })


#  AI PROCTORING: Log events from browser
@require_POST
def log_proctoring_event(request):
    try:
        data = json.loads(request.body)
        exam_key = data.get('exam_key', '').strip()
        roll_no = data.get('roll_no', '').strip()
        event_type = data.get('event_type', '').strip()
        detail = data.get('detail', '')

        if not exam_key or not roll_no or not event_type:
            return JsonResponse({'status': False, 'message': 'Missing fields.'})

        exam = get_object_or_404(Exam, exam_key=exam_key)

        ProctoringEvent.objects.create(
            exam=exam,
            roll_no=roll_no,
            event_type=event_type,
            detail=detail,
        )

        # Count violations for this student
        violation_count = ProctoringEvent.objects.filter(
            exam=exam, roll_no=roll_no
        ).count()

        return JsonResponse({
            'status': True,
            'violation_count': violation_count,
        })
    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)})


#  REAL-TIME ANALYTICS: Dashboard & API
@login_required(login_url='login')
def analytics_dashboard(request, exam_uid):
    exam = get_object_or_404(Exam, uid=exam_uid, teacher=request.user)
    attempts = exam.student_attempts.all().order_by('-updated_at')
    questions = exam.questions.all()

    # ── Per-question analysis ──
    question_stats = []
    for q in questions:
        correct_answers = Answer.objects.filter(question=q, is_correct=True)
        question_stats.append({
            'question': q.question,
            'difficulty': q.difficulty,
            'marks': q.marks,
            'tags': q.get_tag_list(),
        })

    # ── Score distribution ──
    score_ranges = {'0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0}
    for a in attempts.filter(total_marks__gt=0):
        pct = a.percentage
        if pct <= 20:
            score_ranges['0-20'] += 1
        elif pct <= 40:
            score_ranges['21-40'] += 1
        elif pct <= 60:
            score_ranges['41-60'] += 1
        elif pct <= 80:
            score_ranges['61-80'] += 1
        else:
            score_ranges['81-100'] += 1

    # ── Proctoring events summary ──
    proctoring_events = ProctoringEvent.objects.filter(exam=exam).order_by('-timestamp')[:50]
    proctoring_summary = ProctoringEvent.objects.filter(exam=exam).values('event_type').annotate(
        count=Count('uid')
    ).order_by('-count')

    return render(request, 'teacher/analytics.html', {
        'exam': exam,
        'attempts': attempts,
        'questions': questions,
        'question_stats': question_stats,
        'score_ranges': json.dumps(score_ranges),
        'proctoring_events': proctoring_events,
        'proctoring_summary': proctoring_summary,
    })


#  REAL-TIME ANALYTICS: Export CSV
@login_required(login_url='login')
def export_results_csv(request, exam_uid):
    exam = get_object_or_404(Exam, uid=exam_uid, teacher=request.user)
    attempts = exam.student_attempts.all().order_by('roll_no')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{exam.name}_results.csv"'

    writer = csv.writer(response)
    writer.writerow(['Roll No', 'Score', 'Total Marks', 'Percentage', 'Grade', 'Time Taken (s)', 'Submitted', 'Submitted At'])

    for a in attempts:
        writer.writerow([
            a.roll_no,
            a.score,
            a.total_marks,
            f'{a.percentage}%',
            a.grade,
            a.time_taken_seconds,
            'Yes' if a.is_submitted else 'No',
            a.finished_at.strftime('%Y-%m-%d %H:%M') if a.finished_at else '-',
        ])

    return response


#  LMS INTEGRATION: Webhook API for grade sync
def lms_grade_sync(request, exam_uid):
    """API endpoint for LMS platforms to fetch grades."""
    exam = get_object_or_404(Exam, uid=exam_uid)

    if exam.lms_platform == 'none':
        return JsonResponse({'status': False, 'message': 'LMS not configured for this exam.'})

    attempts = exam.student_attempts.filter(is_submitted=True)
    grades = []
    for a in attempts:
        grades.append({
            'roll_no': a.roll_no,
            'score': a.score,
            'total_marks': a.total_marks,
            'percentage': a.percentage,
            'grade': a.grade,
            'submitted_at': a.finished_at.isoformat() if a.finished_at else None,
        })

    return JsonResponse({
        'status': True,
        'exam': exam.name,
        'lms_platform': exam.lms_platform,
        'lms_course_id': exam.lms_course_id,
        'grades': grades,
    })
