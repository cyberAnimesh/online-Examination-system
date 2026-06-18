from django.db import models
from django.contrib.auth.models import User
from Category.models import Category, BaseModel
import random
import uuid
import string

def generate_short_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

#  EXAM MODEL  (+ AI Proctoring, Enterprise Security,
#               LMS Integration settings)
class Exam(BaseModel):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teacher_exams', null=True, blank=True)
    exam_key = models.CharField(max_length=8, unique=True, default=generate_short_key, editable=False)
    is_active = models.BooleanField(default=True)

    # ── AI-Powered Proctoring ──
    proctoring_enabled = models.BooleanField(default=False, help_text='Enable webcam & tab-switch monitoring')

    # ── Enterprise Security ──
    browser_lockdown = models.BooleanField(default=False, help_text='Force fullscreen & block copy/paste')

    # ── Smart Question Bank ──
    shuffle_questions = models.BooleanField(default=True)
    max_questions = models.PositiveIntegerField(default=0, help_text='0 = all questions')

    # ── Timer (Analytics / Exam Config) ──
    time_limit_minutes = models.PositiveIntegerField(default=0, help_text='0 = no time limit')

    # ── LMS Integration ──
    LMS_CHOICES = [
        ('none', 'None'),
        ('moodle', 'Moodle'),
        ('canvas', 'Canvas'),
        ('blackboard', 'Blackboard'),
        ('google_classroom', 'Google Classroom'),
        ('teams', 'Microsoft Teams'),
    ]
    lms_platform = models.CharField(max_length=30, choices=LMS_CHOICES, default='none')
    lms_course_id = models.CharField(max_length=255, blank=True, default='')

    def __str__(self):
        return self.name

    @property
    def total_marks(self):
        return self.questions.aggregate(total=models.Sum('marks'))['total'] or 0

    @property
    def avg_score(self):
        attempts = self.student_attempts.filter(total_marks__gt=0)
        if not attempts.exists():
            return 0
        return round(attempts.aggregate(avg=models.Avg('score'))['avg'] or 0, 1)

    @property
    def pass_rate(self):
        attempts = self.student_attempts.filter(total_marks__gt=0)
        if not attempts.exists():
            return 0
        passed = sum(1 for a in attempts if a.percentage >= 40)
        return round((passed / attempts.count()) * 100, 1)


#  QUESTION MODEL  (Smart Question Bank)
class Question(BaseModel):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='category_questions')
    question = models.TextField()
    marks = models.PositiveIntegerField()

    # ── Smart Question Bank fields ──
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    tags = models.CharField(max_length=500, blank=True, default='', help_text='Comma-separated tags')

    def __str__(self):
        return self.question

    def get_answers(self, include_correctness=True):
        answer_objs = list(Answer.objects.filter(question=self))
        random.shuffle(answer_objs)
        data = []
        for answer_obj in answer_objs:
            item = {
                'uid': str(answer_obj.uid),
                'answer': answer_obj.answer,
            }
            if include_correctness:
                item['is_correct'] = answer_obj.is_correct
            data.append(item)
        return data

    def get_tag_list(self):
        if self.tags:
            return [t.strip() for t in self.tags.split(',') if t.strip()]
        return []


#  ANSWER MODEL
class Answer(BaseModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='question_answers')
    answer = models.TextField()
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.answer


#  STUDENT ATTEMPT  (+ Real-Time Analytics data)
class StudentAttempt(BaseModel):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='student_attempts')
    roll_no = models.CharField(max_length=50)
    score = models.PositiveIntegerField(default=0)
    total_marks = models.PositiveIntegerField(default=0)

    # ── Real-Time Analytics ──
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    is_submitted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('exam', 'roll_no')

    def __str__(self):
        return f'{self.roll_no} - {self.exam.name}'

    @property
    def percentage(self):
        if self.total_marks > 0:
            return round((self.score / self.total_marks) * 100, 2)
        return 0

    @property
    def grade(self):
        pct = self.percentage
        if pct >= 90:
            return 'A+'
        elif pct >= 80:
            return 'A'
        elif pct >= 70:
            return 'B'
        elif pct >= 60:
            return 'C'
        elif pct >= 40:
            return 'D'
        return 'F'


#  PROCTORING EVENT  (AI Proctoring + Enterprise Security)
class ProctoringEvent(BaseModel):
    EVENT_TYPES = [
        ('tab_switch', 'Tab Switch'),
        ('copy_attempt', 'Copy Attempt'),
        ('paste_attempt', 'Paste Attempt'),
        ('right_click', 'Right Click'),
        ('fullscreen_exit', 'Fullscreen Exit'),
        ('face_not_detected', 'Face Not Detected'),
        ('multiple_faces', 'Multiple Faces'),
        ('browser_resize', 'Browser Resize'),
        ('devtools_open', 'DevTools Opened'),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='proctoring_events')
    roll_no = models.CharField(max_length=50)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    detail = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.roll_no} - {self.event_type} @ {self.timestamp}'
