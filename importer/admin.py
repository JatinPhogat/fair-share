from django.contrib import admin
from .models import ImportSession, ImportRow, ImportAnomaly


class ImportRowInline(admin.TabularInline):
    model = ImportRow
    extra = 0
    readonly_fields = ["row_number", "raw_data", "status"]


class ImportAnomalyInline(admin.TabularInline):
    model = ImportAnomaly
    extra = 0


@admin.register(ImportSession)
class ImportSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "group", "status", "uploaded_by", "created_at"]
    list_filter = ["status"]
    inlines = [ImportRowInline]


@admin.register(ImportRow)
class ImportRowAdmin(admin.ModelAdmin):
    list_display = ["session", "row_number", "status"]
    list_filter = ["status"]
    inlines = [ImportAnomalyInline]
