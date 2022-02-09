import jax
import jax.numpy as jnp
import numpy as np
import wandb
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw

from io import BytesIO
from PIL import Image
import numpy as np
import base64

from argparse import ArgumentParser
from einops import rearrange


def log_metrics(metrics, prefix, epoch, do_print=True, do_wandb=True):
    metrics = {m: np.mean(metrics[m]) for m in metrics}

    if do_wandb:
        wandb.log({f'{prefix}/{m}': metrics[m] for m in metrics}, step=epoch)
    if do_print:
        print(f'{prefix}/metrics')
        print(', '.join(f'{k}: {v:.3f}' for k, v in metrics.items()))


def log_segmentation(data, tag, step):
    H, W, C = data['imagery'].shape

    fig, axs = plt.subplots(1, 3, figsize=(10, 3))
    for ax in axs:
        ax.axis('off')
    axs[0].imshow(np.asarray(data['imagery']), cmap='gray')
    axs[1].imshow(np.asarray(data['seg'][:,:,0]), cmap='gray', vmin=-1, vmax=1)
    axs[2].imshow(np.asarray(data['mask']), cmap='gray', vmin=0, vmax=1)

    wandb.log({tag: wandb.Image(fig)}, step=step)
    plt.close(fig)


def log_anim(data, tag, step):
    img = np.clip(255 * data['imagery'], 0, 255).astype(np.uint8)
    img = np.stack([img[..., 0]] * 3, axis=-1)
    H, W, C = img.shape
    img = Image.fromarray(np.asarray(img))
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    imgbase64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    truth = data['contour']
    gtpath = make_path_string(truth)

    path_html = ""
    for pred in data['snake_steps']:
        pred = pred + [pred[-1], pred[-1]]
        path_html += animated_path(pred)

    html = f"""
    <!DOCTYPE html>
    <html>
    <meta charset = "UTF-8">
    <body>
      <svg xmlns="http://www.w3.org/2000/svg" height="100%" viewBox="0 0 256 256">
        <image href="data:image/jpeg;charset=utf-8;base64,{imgbase64}" width="256px" height="256px"/>
        <path fill="none" stroke="rgb(0, 0, 255)" stroke-width="3"
            d="{gtpath}" />
        </path>
        {path_html}
      </svg>
    </body>
    </html>
    """

    wandb.log({tag: wandb.Html(html, inject=False)}, step=step)


def draw_snake(draw, snake, dashed=False, **kwargs):
    if dashed:
        for (y0, x0, y1, x1) in snake.reshape((-1, 4)):
            draw.line((x0, y0, x1, y1), **kwargs)
    else:
        for (y0, x0), (y1, x1) in zip(snake, snake[1:]):
            draw.line((x0, y0, x1, y1), **kwargs)


def make_path_string(vertices):
    return 'M' + ' L'.join(f'{x:.2f},{y:.2f}' for y, x in vertices)


def animated_path(paths):
    pathvalues = ";".join(make_path_string(path) for path in paths)
    keytimes = ";".join(f'{x:.2f}' for x in np.linspace(0, 1, len(paths)))
    return f"""<path fill="none" stroke="rgb(255, 0, 0)" stroke-width="1">
          <animate attributeName="d" values="{pathvalues}" keyTimes="{keytimes}" dur="3s" repeatCount="indefinite" />
          </path>
          """
