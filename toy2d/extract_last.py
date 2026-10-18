from PIL import Image
import os, glob
for gif in glob.glob(os.path.join(os.path.dirname(__file__),'results','*_wide_boundary.gif')):
    im = Image.open(gif)
    im.seek(im.n_frames-1)
    out = gif.replace('_boundary.gif','_final.png')
    im.convert('RGB').save(out)
    print('saved', os.path.basename(out), 'frames=', im.n_frames)
