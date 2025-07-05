from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from .models import User

@csrf_exempt
def show_users(request):
    if request.method == 'GET':
        users = User.objects.all().values('user_id', 'username', 'age', 'point', 'created_at')
        users_list = list(users)
        return JsonResponse(users_list, safe=False)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)
