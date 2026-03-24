from django.urls import path
from . import views

urlpatterns = [
    path('inbox/',                           views.InboxView.as_view()), # InboxView returns the conversation list you see on the Chat tab. Only conversations for the specified lease are returned, and only those that the user is a participant in.
    path('conversations/<int:pk>/',          views.ConversationDetailView.as_view()), # ConversationDetailView returns the conversation metadata along with the first page of messages for that conversation.
    path('conversations/<int:pk>/messages/', views.MessageHistoryView.as_view()), # This endpoint supports paginated loading of older messages when you scroll up in the chat history.
]