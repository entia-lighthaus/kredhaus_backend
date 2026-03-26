from django.urls import path
from . import views


urlpatterns = [
    path('inbox/',                                views.InboxView.as_view()), # InboxView returns the conversation list you see on the Chat tab. Only conversations for the specified lease are returned, and only those that the user is a participant in.
    path('conversations/',                        views.ConversationCreateView.as_view()),   # start a thread. Note: this endpoint is used when you click "Message landlord" or "Message neighbor" from the property or lease details page. It creates a new conversation thread scoped to that context (e.g. lease or property) if one doesn't already exist, and returns the conversation ID so the frontend can open that thread.
    path('conversations/<int:pk>/',               views.ConversationDetailView.as_view()),   # read a thread. ConversationDetailView returns the conversation metadata along with the first page of messages for that conversation.
    path('conversations/<int:pk>/messages/',      views.MessageHistoryView.as_view()),       # paginated history. This endpoint supports paginated loading of older messages when you scroll up in the chat history.
    path('conversations/<int:pk>/messages/send/', views.MessageCreateView.as_view()),        # send a message. Note: this is the REST fallback when WebSocket isn't connected.
]