class Libro:
    def __init__(self, titulo, autor):
        self.titulo = titulo
        self.autor = autor
        self.disponible = True


class Solicitud:
    def __init__(self, libro, estudiante):
        self.libro = libro
        self.estudiante = estudiante
        self.estado = "Activa"


class Biblioteca:
    def __init__(self, nombre):
        self.nombre = nombre
        self.libros = []
        self.solicitudes = []

    def agregar_libro(self, libro):
        self.libros.append(libro)

    def mostrar_libros(self):
        print(f"\nLibros de {self.nombre}:")
        for libro in self.libros:
            estado = "Disponible" if libro.disponible else "Prestado"
            print(f"- {libro.titulo}, de {libro.autor}: {estado}")

    def solicitar_libro(self, libro, estudiante):
        if libro not in self.libros:
            print("Ese libro no pertenece a la biblioteca.")
            return None

        if not libro.disponible:
            print(f"{libro.titulo} ya está prestado.")
            return None

        solicitud = Solicitud(libro, estudiante)
        self.solicitudes.append(solicitud)
        libro.disponible = False
        print(f"{estudiante} solicitó {libro.titulo}.")
        return solicitud

    def devolver_libro(self, solicitud):
        if solicitud not in self.solicitudes or solicitud.estado != "Activa":
            print("La solicitud no está activa en esta biblioteca.")
            return

        solicitud.estado = "Finalizada"
        solicitud.libro.disponible = True
        print(f"{solicitud.estudiante} devolvió {solicitud.libro.titulo}.")


# Prueba del proyecto
biblioteca = Biblioteca("Biblioteca Universitaria")

libro1 = Libro("Cien años de soledad", "Gabriel García Márquez")
libro2 = Libro("El principito", "Antoine de Saint-Exupéry")

biblioteca.agregar_libro(libro1)
biblioteca.agregar_libro(libro2)

biblioteca.mostrar_libros()

solicitud1 = biblioteca.solicitar_libro(libro1, "Ana")
biblioteca.mostrar_libros()

biblioteca.devolver_libro(solicitud1)
biblioteca.mostrar_libros()