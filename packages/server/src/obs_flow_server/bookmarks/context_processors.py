from bookmarks.models import Bookmark

def bookmarks(request):
    if request.user and request.user.is_authenticated:
        return {"bookmarks": Bookmark.objects.filter(user=request.user)}
    return {"bookmarks": []}
