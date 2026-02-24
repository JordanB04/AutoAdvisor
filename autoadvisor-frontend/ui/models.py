from django.db import models

class Student(models.Model):
    name = models.CharField(max_length=255)
    v_number = models.CharField(max_length=20)
    advisor = models.CharField(max_length=255)

class Semester(models.Model):
    student = models.ForeignKey(Student, related_name='semesters', on_delete=models.CASCADE)
    label = models.CharField(max_length=50)
    description = models.TextField()

class Course(models.Model):
    semester = models.ForeignKey(Semester, related_name='courses', on_delete=models.CASCADE)
    course_code = models.CharField(max_length=10)
    name = models.CharField(max_length=255)
    grade = models.CharField(max_length=2)
    credits = models.DecimalField(max_digits=4, decimal_places=3)
    notes = models.TextField()
