from django.contrib import admin

from apps.matching.models import (
    Connection,
    MatchScore,
    ProblemStatement,
    UserProblemSelection,
)


@admin.register(ProblemStatement)
class ProblemStatementAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "category", "is_active", "version"]
    list_filter = ["category", "is_active"]


@admin.register(UserProblemSelection)
class UserProblemSelectionAdmin(admin.ModelAdmin):
    list_display = ["user", "problem_statement", "selected_at"]
    list_filter = ["problem_statement__category"]


@admin.register(MatchScore)
class MatchScoreAdmin(admin.ModelAdmin):
    list_display = ["user_a", "user_b", "total_score", "demographic_score", "problem_score"]
    list_filter = ["total_score"]


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ["requester", "recipient", "status", "created_at"]
    list_filter = ["status"]
