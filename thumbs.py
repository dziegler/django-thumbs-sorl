# -*- encoding: utf-8 -*-
"""
django-thumbs by Antonio Melé
http://django.es
"""
from django.db.models import ImageField
from django.db.models.fields.files import ImageFieldFile
from PIL import Image
from django.core.files.base import ContentFile
from django.conf import settings
import cStringIO

def generate_thumb(img, thumb_size, format, options):
    """
    Generates a thumbnail image and returns a ContentFile object with the thumbnail
    
    Parameters:
    ===========
    img         File object
    
    thumb_size  desired thumbnail size, ie: (200,120)
    
    format      format of the original image ('jpeg','gif','png',...)
                (this format will be used for the generated thumbnail, too)
    """
    
    img.seek(0) # see http://code.djangoproject.com/ticket/8222 for details
    image = Image.open(img)
    
    # Convert to RGB if necessary
    if image.mode not in ('L', 'RGB', 'RGBA'):
        image = image.convert('RGB')
        
    # get size
    thumb_w, thumb_h = thumb_size
    # If you want to generate a square thumbnail
    if 'crop' in options:
        # quad
        xsize, ysize = image.size
        # get minimum size
        minsize = min(xsize,ysize)
        # largest square possible in the image
        xnewsize = (xsize-minsize)/2
        ynewsize = (ysize-minsize)/2
        # crop it
        image2 = image.crop((xnewsize, ynewsize, xsize-xnewsize, ysize-ynewsize))
        # load is necessary after crop                
        image2.load()
        # thumbnail of the cropped image (with ANTIALIAS to make it look better)
        image2.thumbnail(thumb_size, Image.ANTIALIAS)
    else:
        # not quad
        image2 = image
        image2.thumbnail(thumb_size, Image.ANTIALIAS)
    
    io = cStringIO.StringIO()
    # PNG and GIF are the same, JPG is JPEG
    if format.upper()=='JPG':
        format = 'JPEG'
    
    image2.save(io, format)
    return ContentFile(io.getvalue())    

class ExtraThumbnails(object):
    pass
    
class ImageWithThumbsFieldFile(ImageFieldFile):
    """
    See ImageWithThumbsField for usage example
    """
    def __init__(self, instance, field, filename, **kwargs):
        super(ImageWithThumbsFieldFile, self).__init__(instance, field, filename, **kwargs)
        if filename:
            setattr(self, 'thumbnail', settings.MEDIA_URL + self._get_thumb_name(self.field.thumbnail_args))
            if self.field.extra_thumbnails:
                setattr(self, 'extra_thumbnails',ExtraThumbnails())
            for name, thumb_args in self.field.extra_thumbnails.iteritems():
                setattr(self.extra_thumbnails, name, settings.MEDIA_URL + self._get_thumb_name(thumb_args))
            
    def save(self, name, content, save=True):
        super(ImageWithThumbsFieldFile, self).save(name, content, save)
        self._save(self.field.thumbnail_args, content)
        for name, thumb_args in self.field.extra_thumbnails.iteritems():
            self._save(thumb_args, content)
        
    def _save(self, thumb_args, content):        
        options = thumb_args.get('options',())
        thumb_name = self._get_thumb_name(thumb_args)
        thumb_content = generate_thumb(content, thumb_args['size'], self.name.rsplit('.',1)[1], options)
        thumb_name_ = self.storage.save(thumb_name, thumb_content)        
        
        if not thumb_name == thumb_name_:
            raise ValueError('There is already a file named %s' % thumb_name)
        
    def delete(self, save=True):
        self._delete('thumbnail', self.field.thumbnail_args)
        for name, thumb_args in self.field.extra_thumbnails.iteritems():
            self._delete(name, thumb_args)
        super(ImageWithThumbsFieldFile, self).delete(save)
            
    def _delete(self, name, thumb_args):        
        thumb_name = self._get_thumb_name(thumb_args)
        self.storage.delete(thumb_name)
            
    def _get_thumb_name(self, thumb_args):
        (w,h) = thumb_args['size']
        options = thumb_args.get('options',())
        split = self.name.rsplit('.',1)
        return '%s.%s' % ('_'.join((split[0],str(w),str(h),'_'.join(options))),split[1])
                
class ImageWithThumbsField(ImageField):
    attr_class = ImageWithThumbsFieldFile
    """
    Usage example:
    ==============
    photo = ImageWithThumbsField(upload_to='images', sizes=((125,125),(300,200),)
    
    To retrieve image URL, exactly the same way as with ImageField:
        my_object.photo.url
    To retrieve thumbnails URL's just add the size to it:
        my_object.photo.url_125x125
        my_object.photo.url_300x200
    
    Note: The 'sizes' attribute is not required. If you don't provide it, 
    ImageWithThumbsField will act as a normal ImageField
        
    How it works:
    =============
    For each size in the 'sizes' atribute of the field it generates a 
    thumbnail with that size and stores it following this format:
    
    available_filename.[width]x[height].extension

    Where 'available_filename' is the available filename returned by the storage
    backend for saving the original file.
    
    Following the usage example above: For storing a file called "photo.jpg" it saves:
    photo.jpg          (original file)
    photo.125x125.jpg  (first thumbnail)
    photo.300x200.jpg  (second thumbnail)
    
    With the default storage backend if photo.jpg already exists it will use these filenames:
    photo_.jpg
    photo_.125x125.jpg
    photo_.300x200.jpg
    
    Note: django-thumbs assumes that if filename "any_filename.jpg" is available 
    filenames with this format "any_filename.[widht]x[height].jpg" will be available, too.
    
    To do:
    ======
    Add method to regenerate thubmnails
    
    """
    def __init__(self, verbose_name=None, name=None, width_field=None, height_field=None, thumbnail=None, extra_thumbnails=None, **kwargs):
        self.verbose_name=verbose_name
        self.name=name
        self.width_field=width_field
        self.height_field=height_field
        self.thumbnail_args = thumbnail
        self.extra_thumbnails = extra_thumbnails
        super(ImageField, self).__init__(**kwargs)
