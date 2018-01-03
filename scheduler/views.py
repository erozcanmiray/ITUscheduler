from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render_to_response
from django.views import generic
from api.models import CourseCode, Course
from scheduler.models import Schedule
from scheduler.forms import ScheduleForm, CustomUserCreationForm


class IndexView(generic.CreateView):
    form_class = ScheduleForm
    template_name = "index.html"
    success_url = "."

    @staticmethod
    def is_available(courses, course):
        if course.is_full():
            return False
        for c in courses:
            if course.day == c.day and c.time[0] <= course.time[0] <= c.time[1] or c.time[0] <= course.time[1] <= c.time[1]:
                return False
            else:
                continue
        return True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user = self.request.user
        if user.is_authenticated:
            kwargs["courses"] = user.courses
            _ = [
                "8:30-9:29",
                "9:30-10:29",
                "10:30-11:29",
                "11:30-12:29",
                "12:30-13:29",
                "13:30-14:29",
                "14:30-15:29",
                "15:30-16:29",
                "16:30-17:29",
                "17:30-18:29",
                "18:30-19:29",
                "19:30-20:29"
            ]
            if self.request.method == "POST":
                post_data = kwargs["data"].copy()
                post_data["user"] = user.id
                kwargs["data"] = post_data
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if not user.my_schedule:
            return context
        class Hour:
            def __init__(self, time, time_start, time_finish, course=None):
                self.time = time
                self.time_start = time_start
                self.time_finish = time_finish
                self.course = course
        if user.is_authenticated:
            hours = [
                Hour("8:30-9:29", 830, 929),
                Hour("9:30-10:29", 930, 1029),
                Hour("10:30-11:29", 1030, 1129),
                Hour("11:30-12:29", 1130, 1229),
                Hour("12:30-13:29", 1230, 1329),
                Hour("13:30-14:29", 1330, 1429),
                Hour("14:30-15:29", 1430, 1529),
                Hour("15:30-16:29", 1530, 1629),
                Hour("16:30-17:29", 1630, 1729),
                Hour("17:30-18:29", 1730, 1829),
                Hour("18:30-19:29", 1830, 1929),
                Hour("19:30-20:29", 1930, 2029),
                Hour("20:30-21:29", 2030, 2129)
            ]
            for hour in hours:
                for course in user.my_schedule.courses.all():
                    r = range(int(course.time_start), int(course.time_finish))
                    if hour.time_start in r and hour.time_finish in r:
                        hour.course = course
            context["hours"] = hours
            context["my_schedule"] = user.my_schedule
            context["my_courses"] = user.my_schedule.courses.all()
            context["courses"] = user.courses.all()
            schedules = Schedule.objects.filter(user=user).all()
            context["schedules"] = schedules
            try:
                selected_schedule = schedules[0]
            except IndexError:
                selected_schedule = 0
            for schedule in schedules:
                if str(schedule.id) in self.request.path:
                    selected_schedule = schedule
                    break
                elif schedule == user.my_schedule:
                    selected_schedule = schedule
                    break
            context["selected_schedule"] = selected_schedule
        return context


class CoursesView(generic.DetailView):
    model = CourseCode
    slug_url_kwarg = "slug"
    template_name = "courses.html"

    def get_slug_field(self):
        return "code"

    def dispatch(self, request, *args, **kwargs):
        if not CourseCode.objects.all() or not Course.objects.filter(course_code=kwargs["slug"]).all():
            return render_to_response("courses.html", context={"request": request, "user": request.user, "course_codes": CourseCode.objects.all()})
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course_codes"] = CourseCode.objects.all()
        courses = context["object"].course_set.all()
        for course in courses:
            course.times = []
            for i in range(course.n_classes):
                course.times.append("{}/{} ".format(course.time_start.split(",")[i], course.time_finish.split(",")[i]))
        context["courses"] = courses
        if self.request.user.is_authenticated:
            context["my_courses"] = [course.crn for course in self.request.user.courses.all()]
        context["refreshed"] = context["object"].refreshed
        return context


class RegistrationView(generic.FormView):
    form_class = CustomUserCreationForm
    template_name = "registration/signup.html"
    success_url = "/"

    def form_valid(self, form):
        form.save()
        user = authenticate(username=form.cleaned_data["username"], password=form.cleaned_data["password1"])
        login(self.request, user)
        return super().form_valid(form)


@login_required
def add_course(request):
    try:
        course_crn = int(request.POST["course_crn"])
        course = Course.objects.get(crn=course_crn)
        my_courses = request.user.courses
        if course in my_courses.all():
            my_courses.remove(course.crn)
        else:
            my_courses.add(course.crn)
        return JsonResponse({"courses": [course.crn for course in request.user.courses.all()], "successful": True})
    except Exception as error:
        return JsonResponse({"courses": [course.crn for course in request.user.courses.all()], "successful": False, "error": error})


@login_required
def select_schedule(request):
    try:
        schedule_id = int(request.POST["schedule_id"])
        schedule = Schedule.objects.get(id=schedule_id)
        request.user.my_schedule = schedule
        request.user.save()
    except Exception as error:
        return JsonResponse({"successful": False, "error": str(error)})
    return JsonResponse({"successful": True, "scheduleId": schedule_id})