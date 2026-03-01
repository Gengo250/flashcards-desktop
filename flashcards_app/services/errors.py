class AppError(Exception):
    """Erro base da aplicação."""


class CsvFormatError(AppError):
    """CSV inválido ou fora do padrão esperado."""