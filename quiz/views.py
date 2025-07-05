from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Quiz

@csrf_exempt
def show_quizzes(request):
    if request.method == 'GET':
        quizzes = Quiz.objects.all().values('quiz_id', 'quiz_image', 'quiz_answer', 'quiz_list')
        quizzes_list = list(quizzes)
        return JsonResponse(quizzes_list, safe=False)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)
