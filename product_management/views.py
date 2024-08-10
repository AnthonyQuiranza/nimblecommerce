import os
from django.conf import settings
from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .woocommerce_api import WooCommerceAPI
from django.contrib import messages
from math import ceil
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import base64
import uuid
from django.views.decorators.csrf import csrf_exempt
import json 


@login_required
def get_product_details(request, product_id):
    api = WooCommerceAPI()
    product = api.get_product(product_id)
    if product:
        return JsonResponse({
            'id': product['id'],
            'name': product['name'],
            'price': product['price'],
            'description': product['description'],
            'category': product['categories'][0]['id'] if product['categories'] else '',
        })
    return JsonResponse({'error': 'Producto no encontrado'}, status=404)


@login_required
def edit_product(request):
    if request.method == 'POST':
        api = WooCommerceAPI()
        product_id = request.POST.get('id')
        product_data = {
            'name': request.POST.get('name'),
            'regular_price': request.POST.get('price'),
            'description': request.POST.get('description'),
            'categories': [{'id': int(request.POST.get('category'))}],
        }
        response = api.update_product(product_id, product_data)
        if 'id' in response:
            return JsonResponse({'success': True, 'message': 'Producto actualizado correctamente'})
        else:
            return JsonResponse({'success': False, 'message': 'Error al actualizar el producto'})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})



@login_required
def product_list(request):
    api = WooCommerceAPI()
    page = request.GET.get('page', 1)
    per_page = 10
    category = request.GET.get('category')
    search = request.GET.get('search')

    products, headers = api.get_products(page=page, per_page=per_page, category=category, search=search)
    total_products = int(headers.get('X-WP-Total', 0))
    
    paginator = Paginator(range(total_products), per_page)
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    # Calcular el rango de páginas a mostrar
    max_pages = 5
    current_page = products_page.number
    page_range = list(paginator.page_range)
    if len(page_range) > max_pages:
        start = max(0, current_page - max_pages // 2 - 1)
        end = start + max_pages
        if end > len(page_range):
            end = len(page_range)
            start = max(0, end - max_pages)
        page_range = page_range[start:end]

    context = {
        'products': products,
        'page_obj': products_page,
        'paginator': paginator,
        'page_range': page_range,
        'categories': api.get_categories(),
        'category': category,
        'search': search,
    }
    return render(request, 'product_management/product_list.html', context)


@csrf_exempt
@login_required
def add_product(request):
    if request.method == 'GET':
        # Renderizar el formulario para añadir producto
        api = WooCommerceAPI()
        categories = api.get_categories()  # Asumiendo que tienes un método para obtener categorías
        return render(request, 'product_management/add_product.html', {'categories': categories})
    
    elif request.method == 'POST':
        try:
            api = WooCommerceAPI()
            
            name = request.POST.get('name')
            price = request.POST.get('price')
            description = request.POST.get('description')
            short_description = request.POST.get('short_description')
            category_id = request.POST.get('category')
            
            # Validaciones
            if not name:
                raise ValidationError("El nombre del producto es obligatorio.")
            if not price or not price.replace('.', '').isdigit():
                raise ValidationError("El precio debe ser un número válido.")
            if not description:
                raise ValidationError("La descripción del producto es obligatoria.")
            if not category_id:
                raise ValidationError("Debes seleccionar una categoría.")
            if 'mainImage' not in request.FILES:
                raise ValidationError("Debes subir una imagen principal del producto.")

            # Manejar la imagen principal
            main_image = request.FILES.get('mainImage')
            main_image_data = None
            if main_image:
                main_image_data = api.upload_image(main_image)
                if main_image_data['id'] is None:
                    return JsonResponse({'success': False, 'message': f"Error al subir la imagen principal: {main_image_data['error']}"})
            
            # Manejar imágenes adicionales
            additional_images_data = []
            for key, file in request.FILES.items():
                if key.startswith('additionalImage_'):
                    add_image_data = api.upload_image(file)
                    if add_image_data['id'] is None:
                        return JsonResponse({'success': False, 'message': f"Error al subir imagen adicional: {add_image_data['error']}"})
                    additional_images_data.append(add_image_data)
            
            # Preparar datos del producto
            product_data = {
                'name': name,
                'type': 'simple',
                'regular_price': price,
                'description': description,
                'short_description': short_description,
                'categories': [{'id': int(category_id)}] if category_id else [],
                'images': [{'id': main_image_data['id']}] if main_image_data else []
            }
            
            # Añadir imágenes adicionales
            for img_data in additional_images_data:
                product_data['images'].append({'id': img_data['id']})
            
            # Crear el producto
            response = api.create_product(product_data)
            
            if 'id' in response:
                return JsonResponse({'success': True, 'message': 'Producto añadido exitosamente'})
            else:
                return JsonResponse({'success': False, 'message': 'Error al crear el producto: ' + json.dumps(response)})
        
        except Exception as e:
            import traceback
            error_message = f"Error inesperado: {str(e)}\n{traceback.format_exc()}"
            print(error_message)
            return JsonResponse({'success': False, 'message': f'Error inesperado: {str(e)}'})
    
    else:

        return JsonResponse({'success': False, 'message': 'Método no permitido'})


def handle_uploaded_file(f, request):
    file_name = f"{uuid.uuid4()}.{f.name.split('.')[-1]}"
    file_path = default_storage.save(f'product_images/{file_name}', f)
    return request.build_absolute_uri(default_storage.url(file_path))



@csrf_exempt
def upload_image(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        
        # Generar un nombre de archivo único
        filename = f"{uuid.uuid4().hex}_{uploaded_file.name}"
        
        # Definir la ruta donde se guardará la imagen
        filepath = os.path.join('product_images', filename)
        
        # Guardar el archivo
        path = default_storage.save(filepath, ContentFile(uploaded_file.read()))
        
        # Construir la URL completa del archivo
        file_url = settings.MEDIA_URL + path
        
        return JsonResponse({
            'success': True,
            'file_name': filename,
            'file_url': file_url
        })
    
    return JsonResponse({'success': False, 'error': 'No file was uploaded'}, status=400)
