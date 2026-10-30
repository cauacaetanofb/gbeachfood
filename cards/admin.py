from django.contrib import admin
from .models import Recarga


@admin.register(Recarga)
class RecargaAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'valor', 'metodo', 'status', 'evento_revisao', 'criado_em')
    list_filter = ('metodo', 'status')
    search_fields = ('asaas_payment_id', 'user__username')
    readonly_fields = tuple(field.name for field in Recarga._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
