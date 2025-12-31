# logic/__init__.py
"""
Evitar re-exports en import-time para no crear ciclos.
Importa SIEMPRE desde submódulos explícitos:
  from logic.expenses import expense_list_view, ...
  from logic.invoices import invoice_list_view, ...
"""
__all__ = []