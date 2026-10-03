# Rifter

Reproductor para practicar instrumentos con canciones de YouTube. Muestra la onda completa de la canción, permite marcar checkpoints anidados (canción → periodos → fragmentos) y repetir cualquiera en bucle sin cortes.

## Descargar (app de escritorio)

Instaladores para macOS, Linux y Windows en [Releases](https://github.com/ivanroosvelt/rifter/releases).

> **macOS:** la app no está firmada por Apple y macOS dirá que está "dañada". Después de arrastrarla a Aplicaciones, ejecuta una vez en la terminal:
>
> ```sh
> xattr -cr /Applications/Rifter.app
> ```
>
> y ábrela normal. En Windows, SmartScreen: "Más información → Ejecutar de todos modos".

## Arrancar

Requiere [uv](https://docs.astral.sh/uv/), `ffmpeg` y `deno` en el PATH (uv instala yt-dlp solo).

```sh
brew install ffmpeg deno   # macOS
uv run server.py
```

Abre http://localhost:8000

## Uso

1. Escribe una búsqueda (o pega una URL de YouTube) y pulsa **Buscar**.
2. Pasa el mouse por un resultado para oír 15 s de vista previa; haz click para cargarlo.
3. Onda superior: canción completa. Onda inferior: zoom de la sección en bucle.
4. **Arrastra** sobre la onda para crear un checkpoint. Se anida solo dentro del que lo contiene y adopta los que queden dentro.
5. Click en una barra o en el árbol de la derecha para repetir esa sección.

### Teclado

| Tecla | Acción |
|---|---|
| Espacio | Play / pausa |
| 1–9 | Periodo n |
| ⇧ 1–9 | Fragmento n del periodo actual |
| 0 | Canción completa |
| ← → | Sección anterior / siguiente |
| ↑ / ↓ | Checkpoint padre / primer hijo |
| [ y luego ] | Crear sección marcando inicio y fin mientras suena |

Doble click en el árbol: renombrar. ✕: borrar (sus hijos suben un nivel).

## Datos

Todo queda en `./data`:

- `<id>.mp3` — audio descargado (caché)
- `<id>.json` — checkpoints de la canción, se guardan solos
- `pv/<id>.mp3` — vistas previas

La URL (`#<id>`) recarga la misma canción.

## Cómo funciona

- `server.py` — servidor Python sin dependencias que usa [yt-dlp](https://github.com/yt-dlp/yt-dlp) para buscar y descargar el audio, y guarda los checkpoints.
- `index.html` — todo el reproductor. Dibuja la onda con Canvas y usa Web Audio para que el bucle sea exacto al sample.

## Problemas

Si YouTube deja de descargar, actualiza yt-dlp refrescando el caché de uv:

```sh
uv run --refresh server.py
```
