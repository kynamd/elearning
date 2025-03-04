import requests
import datetime

from django import forms
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, F, Sum, FloatField, Avg
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic.base import TemplateResponseMixin, View
from django.forms.models import modelform_factory
from django.apps import apps
from braces.views import LoginRequiredMixin, PermissionRequiredMixin, CsrfExemptMixin, JsonRequestResponseMixin
from django.core.urlresolvers import reverse_lazy, reverse
from django.views.generic.list import ListView
from .models import Course, Module, Content, Subject, Review, Cluster
from .forms import ModuleFormSet, ReviewForm, CourseCreateForm
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from students.forms import CourseEnrollForm
from django.utils.decorators import method_decorator
from students.decorators import teacher_required
from django.core.cache import cache
from courses.forms import UserEditForm

from courses.search import youtube_search
from courses.suggestions import update_clusters

@login_required
def edit(request):
    if request.method == 'POST':
        user_form = UserEditForm(instance=request.user, data=request.POST)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, _('Profile updated successfully'))
    else:
        user_form = UserEditForm(instance=request.user)
    return render(request, 'registration/edit.html', {'user_form': user_form})

@login_required
def list_videos(request):
    subjects = Subject.objects.all()
    videos = []
    q  = None
    max_lengths = [10, 15, 20, 25, 30, 50]
    results = None
    if 'q' and 'results' in request.GET:
        q = request.GET['q']
        results = request.GET['results']
        videos =  youtube_search(q, results)
    return render(request,'videos/list.html', {'videos': videos, 'q': q, 'results': results, 'subjects': subjects, 'max_lengths': max_lengths})


class CourseListView(TemplateResponseMixin, View):
    model = Course
    template_name = 'courses/course/list.html'

    def get(self, request, subject=None):
        # subjects = Subject.objects.annotate(total_courses=Count('courses'))
        # courses = Course.objects.annotate(total_modules=Count('modules'))

        # if subject:
            # subject = get_object_or_404(Subject, slug=subject)
            # courses = courses.filter(subject=subject)
        subjects = cache.get('all_subjects')

        if not subjects:
            subjects = Subject.objects.annotate(total_courses=Count('courses'))
            cache.set('all_subjects', subjects)
        all_courses = Course.objects.annotate(total_modules=Count('modules', distinct=True)).annotate(total_reviews=Count('reviews', distinct=True)).annotate(average_rating=Avg(F('reviews__rating'), distinct=True))
        # subjects = Course.objects.annotate(total_modules=Count('courses'))
        # courses = Course.objects.annotate(total_modules=Count('modules'))

        if subject:
            subject = get_object_or_404(Subject, slug=subject)
            key = 'subject_{}_courses'.format(subject.id)
            courses = cache.get(key)
            if not courses:
                courses = all_courses.filter(subject=subject)
                cache.set(key, courses)
        else:
            courses = cache.get('all_courses')
            if not courses:
                courses = all_courses
                cache.set('all_courses', courses)
        return self.render_to_response({'subjects': subjects, 'subject': subject, 'courses': courses})

class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course/detail.html'

    def get_context_data(self, **kwargs):
        context = super(CourseDetailView, self).get_context_data(**kwargs)
        context['enroll_form'] = CourseEnrollForm(initial={'course': self.object})
        context['review_form'] = ReviewForm()
        context['reviews'] = Review.objects.order_by('-pub_date')[:9]
        return context


def add_review(request, subject):
    subject = get_object_or_404(Course, slug=subject)
    form = ReviewForm(request.POST)
    if form.is_valid():
        rating = form.cleaned_data['rating']
        comment = form.cleaned_data['comment']
        review = Review()
        review.course = subject
        review.user_name = request.user
        review.rating = rating
        review.comment = comment
        review.pub_date = datetime.datetime.now()
        review.save()
        update_clusters()
        messages.success(request, 'Review added.')
        return HttpResponseRedirect(reverse('course_detail', args=(subject.slug,)))
    else:
        messages.warning(request, 'Error Occured.')
        return HttpResponseRedirect(reverse('course_detail', args=(subject.slug,)))
    return render(request, 'courses/course/detail.html', {'subject': subject, 'form': form})


class ModuleOrderView(CsrfExemptMixin, JsonRequestResponseMixin, View):

    def post(self, request):
        for id, order in self.request_json.items():
            Module.objects.filter(id=id, course__owner=request.user).update(order=order)
        return self.render_json_response({'saved': 'OK'})


class ContentOrderView(CsrfExemptMixin, JsonRequestResponseMixin, View):

    def post(self, request):
        for id, order in self.request_json.items():
            Content.objects.filter(id=id, module__course__owner=request.user).update(order=order)
        return self.render_json_response({'saved': 'OK'})

class ContentCreateUpdateView(TemplateResponseMixin, View):
    module = None
    model = None
    obj = None
    template_name = 'courses/manage/content/form.html'

    def get_model(self, model_name):
        if model_name in ['text', 'video', 'image', 'file',]:
            return apps.get_model(app_label='courses', model_name=model_name)
        return None

    def get_form(self, model, *args, **kwargs):
        Form = modelform_factory(model, exclude=['owner', 'order', 'created', 'updated'], widgets={'title': forms.TextInput(attrs={'class':'form-control'}), 'content': forms.Textarea(attrs={'class':'form-control', 'cols': 40, 'rows': 8}), 'url': forms.TextInput(attrs={'class':'form-control'})})

        return Form(*args, **kwargs)

    def dispatch(self, request, module_id, model_name, id=None):
        self.module = get_object_or_404(Module, id=module_id, course__owner=request.user)
        self.model = self.get_model(model_name)

        if id:
            self.obj = get_object_or_404(self.model, id=id, owner=request.user)

        return super(ContentCreateUpdateView, self).dispatch(request, module_id, model_name, id)

    def get(self, request, module_id, model_name, id=None):
        form = self.get_form(self.model, instance=self.obj)
        return self.render_to_response({ 'form':form, 'object': self.obj })

    def post(self, request, module_id, model_name, id=None):
        form = self.get_form(self.model, instance=self.obj, data=request.POST, files=request.FILES)

        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            if not id:
                Content.objects.create(module=self.module, item=obj)
            return redirect('module_content_list', self.module.id)

        return self.render_to_response({ 'form': form, 'object': self.obj })


class ContentDeleteView(View):

    def post(self, request, id):
        content = get_object_or_404(Content, id=id, module__course__owner=request.user)
        module = content.module
        content.item.delete()
        content.delete()
        return redirect('module_content_list', module.id)


class ModuleContentListView(TemplateResponseMixin, View):
    template_name = 'courses/manage/module/content_list.html'

    def get(self, request, module_id):
        module = get_object_or_404(Module, id=module_id, course__owner=request.user)

        return self.render_to_response({'module': module})


class CourseModuleUpdateView(TemplateResponseMixin, View):
    template_name = 'courses/manage/module/formset.html'
    course = None

    def get_formset(self, data=None):
        return ModuleFormSet(instance=self.course, data=data)

    def dispatch(self, request, pk):
        self.course = get_object_or_404(Course, id=pk, owner=request.user)
        return super(CourseModuleUpdateView, self).dispatch(request, pk)

    def get(self, request, *args, **kwargs):
        formset = self.get_formset()
        return self.render_to_response({ 'course': self.course, 'formset': formset })

    def post(self, request, *args, **kwargs):
        formset = self.get_formset(data=request.POST)

        if formset.is_valid():
            formset.save()
            return redirect('manage_course_list')
        return self.render_to_response({ 'course': self.course, 'formset': formset })

class OwnerMixin(object):
    def get_queryset(self):
        qs = super(OwnerMixin, self).get_queryset()
        return qs.filter(owner=self.request.user)


class OwnerEditMixin(object):
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super(OwnerEditMixin, self).form_valid(form)


class OwnerCourseMixin(OwnerMixin, LoginRequiredMixin):
    model = Course
    # fields = ['subject', 'title', 'overview',]
    success_url = reverse_lazy('manage_course_list')


class OwnerCourseEditMixin(OwnerCourseMixin, OwnerEditMixin):
    # fields = ['subject', 'title', 'overview', ]
    form_class = CourseCreateForm
    success_url = reverse_lazy('manage_course_list')
    template_name = 'courses/manage/course/form.html'


@method_decorator([login_required, teacher_required], name='dispatch')
class ManageCourseListView(OwnerCourseMixin, ListView):
    model = Course
    template_name = 'courses/manage/course/list.html'

    def get_queryset(self):
        qs = super(ManageCourseListView, self).get_queryset()
        return qs.filter(owner=self.request.user)


@method_decorator([login_required, teacher_required], name='dispatch')
class CourseCreateView(OwnerCourseEditMixin, CreateView):
    permission_required = 'courses.add_course'


@method_decorator([login_required, teacher_required], name='dispatch')
class CourseUpdateView(OwnerCourseEditMixin, UpdateView):
    template_name = 'courses/manage/course/form.html'
    permission_required = 'courses.change_course'


@method_decorator([login_required, teacher_required], name='dispatch')
class CourseDeleteView(OwnerCourseMixin, DeleteView):
    template_name = 'courses/manage/course/delete.html'
    success_url = reverse_lazy('manage_course_list')
    permission_required = 'courses.delete_course'
