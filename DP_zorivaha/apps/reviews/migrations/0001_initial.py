# Generated migration for reviews app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bookings', '0006_remove_infants_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='обновлено')),
                ('overall_rating', models.PositiveSmallIntegerField(choices=[(1, '1 — Ужасно'), (2, '2 — Плохо'), (3, '3 — Нормально'), (4, '4 — Хорошо'), (5, '5 — Отлично')], help_text='Общее впечатление от проживания', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='общая оценка')),
                ('cleanliness_rating', models.PositiveSmallIntegerField(choices=[(1, '1 — Ужасно'), (2, '2 — Плохо'), (3, '3 — Нормально'), (4, '4 — Хорошо'), (5, '5 — Отлично')], validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='чистота')),
                ('comfort_rating', models.PositiveSmallIntegerField(choices=[(1, '1 — Ужасно'), (2, '2 — Плохо'), (3, '3 — Нормально'), (4, '4 — Хорошо'), (5, '5 — Отлично')], validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='комфорт')),
                ('staff_rating', models.PositiveSmallIntegerField(choices=[(1, '1 — Ужасно'), (2, '2 — Плохо'), (3, '3 — Нормально'), (4, '4 — Хорошо'), (5, '5 — Отлично')], validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='персонал')),
                ('value_rating', models.PositiveSmallIntegerField(choices=[(1, '1 — Ужасно'), (2, '2 — Плохо'), (3, '3 — Нормально'), (4, '4 — Хорошо'), (5, '5 — Отлично')], validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='соотношение цена/качество')),
                ('location_rating', models.PositiveSmallIntegerField(choices=[(1, '1 — Ужасно'), (2, '2 — Плохо'), (3, '3 — Нормально'), (4, '4 — Хорошо'), (5, '5 — Отлично')], validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='расположение')),
                ('title', models.CharField(help_text='Краткое описание впечатления', max_length=200, verbose_name='заголовок')),
                ('text', models.TextField(help_text='Подробный отзыв о проживании', verbose_name='текст отзыва')),
                ('pros', models.TextField(blank=True, help_text='Что понравилось', verbose_name='достоинства')),
                ('cons', models.TextField(blank=True, help_text='Что не понравилось', verbose_name='недостатки')),
                ('status', models.CharField(choices=[('pending', 'На модерации'), ('approved', 'Одобрен'), ('rejected', 'Отклонен')], db_index=True, default='pending', max_length=20, verbose_name='статус')),
                ('moderated_at', models.DateTimeField(blank=True, null=True, verbose_name='дата модерации')),
                ('moderation_comment', models.TextField(blank=True, help_text='Причина отклонения или заметки', verbose_name='комментарий модератора')),
                ('is_featured', models.BooleanField(default=False, help_text='Показывать на главной странице', verbose_name='избранный')),
                ('published_at', models.DateTimeField(blank=True, null=True, verbose_name='дата публикации')),
                ('guest_name', models.CharField(help_text='Имя на момент написания отзыва', max_length=200, verbose_name='имя гостя')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP адрес')),
                ('user_agent', models.TextField(blank=True, verbose_name='User Agent')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to=settings.AUTH_USER_MODEL, verbose_name='автор')),
                ('booking', models.OneToOneField(help_text='Отзыв привязан к конкретному бронированию', on_delete=django.db.models.deletion.CASCADE, related_name='review', to='bookings.booking', verbose_name='бронирование')),
                ('moderated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='moderated_reviews', to=settings.AUTH_USER_MODEL, verbose_name='модератор')),
            ],
            options={
                'verbose_name': 'отзыв',
                'verbose_name_plural': 'отзывы',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['status', '-created_at'], name='reviews_rev_status_idx'),
                    models.Index(fields=['author', '-created_at'], name='reviews_rev_author_idx'),
                    models.Index(fields=['is_featured', 'status'], name='reviews_rev_featured_idx'),
                    models.Index(fields=['-overall_rating', 'status'], name='reviews_rev_rating_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='ReviewResponse',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='обновлено')),
                ('text', models.TextField(help_text='Ответ администрации на отзыв', verbose_name='текст ответа')),
                ('author_name', models.CharField(help_text='Имя сотрудника для отображения', max_length=200, verbose_name='имя автора')),
                ('author_position', models.CharField(blank=True, help_text='Например: Администратор, Менеджер', max_length=100, verbose_name='должность')),
                ('author', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='review_responses', to=settings.AUTH_USER_MODEL, verbose_name='автор ответа')),
                ('review', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='response', to='reviews.review', verbose_name='отзыв')),
            ],
            options={
                'verbose_name': 'ответ на отзыв',
                'verbose_name_plural': 'ответы на отзывы',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ReviewModeration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='обновлено')),
                ('action', models.CharField(choices=[('approved', 'Одобрен'), ('rejected', 'Отклонен'), ('edited', 'Отредактирован'), ('deleted', 'Удален')], max_length=20, verbose_name='действие')),
                ('comment', models.TextField(blank=True, verbose_name='комментарий')),
                ('snapshot', models.JSONField(blank=True, default=dict, help_text='Состояние отзыва на момент действия', verbose_name='снимок данных')),
                ('moderator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='review_moderation_actions', to=settings.AUTH_USER_MODEL, verbose_name='модератор')),
                ('review', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='moderation_history', to='reviews.review', verbose_name='отзыв')),
            ],
            options={
                'verbose_name': 'история модерации',
                'verbose_name_plural': 'история модерации',
                'ordering': ['-created_at'],
            },
        ),
    ]
