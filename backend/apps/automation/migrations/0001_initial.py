import uuid
import apps.automation.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('channels_integration', '0002_add_channel_platforms'),
    ]

    operations = [
        migrations.CreateModel(
            name='CloudMediaManager',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(upload_to=apps.automation.models._media_upload_path)),
                ('file_name', models.CharField(editable=False, max_length=255)),
                ('media_type', models.CharField(
                    choices=[('image', 'Image'), ('video', 'Video')],
                    default='image',
                    max_length=10,
                )),
                ('is_used', models.BooleanField(db_index=True, default=False)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('used_in_post_id', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('workspace', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='media_files',
                    to='accounts.workspace',
                )),
            ],
            options={
                'verbose_name': 'Cloud Media',
                'verbose_name_plural': 'Cloud Media',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='AutoPostConfig',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('is_auto_post_enabled', models.BooleanField(default=False)),
                ('post_time', models.TimeField(default='09:00', help_text='UTC time to publish the daily post (HH:MM).')),
                ('niche_keywords', models.CharField(
                    blank=True,
                    help_text="Comma-separated keywords (e.g. 'fitness, weight loss, gym').",
                    max_length=300,
                )),
                ('custom_caption_prompt', models.TextField(blank=True)),
                ('last_post_date', models.DateField(blank=True, null=True)),
                ('total_posts_published', models.PositiveIntegerField(default=0)),
                ('spam_deletion_enabled', models.BooleanField(default=True)),
                ('auto_reply_enabled', models.BooleanField(default=True)),
                ('moderation_prompt', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('workspace', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='auto_post_configs',
                    to='accounts.workspace',
                )),
                ('integration', models.OneToOneField(
                    limit_choices_to={'platform__in': ['messenger', 'instagram']},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='auto_post_config',
                    to='channels_integration.channelintegration',
                )),
            ],
            options={
                'verbose_name': 'Auto-Post Config',
                'verbose_name_plural': 'Auto-Post Configs',
            },
        ),
        migrations.CreateModel(
            name='CommentModerationLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('comment_id', models.CharField(db_index=True, max_length=100)),
                ('post_id', models.CharField(blank=True, max_length=100)),
                ('author_id', models.CharField(blank=True, max_length=100)),
                ('author_name', models.CharField(blank=True, max_length=200)),
                ('comment_text', models.TextField()),
                ('ai_verdict', models.CharField(
                    choices=[('spam', 'Spam'), ('abusive', 'Abusive'), ('valid', 'Valid')],
                    max_length=20,
                )),
                ('ai_reply', models.TextField(blank=True)),
                ('action', models.CharField(
                    choices=[
                        ('deleted', 'Deleted (spam/abusive)'),
                        ('replied', 'Replied (valid)'),
                        ('ignored', 'Ignored (no action)'),
                        ('error', 'Error'),
                    ],
                    max_length=20,
                )),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('workspace', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='moderation_logs',
                    to='accounts.workspace',
                )),
                ('integration', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='moderation_logs',
                    to='channels_integration.channelintegration',
                )),
            ],
            options={
                'verbose_name': 'Comment Moderation Log',
                'verbose_name_plural': 'Comment Moderation Logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='DailyPostLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(
                    choices=[
                        ('success', 'Success'),
                        ('failed', 'Failed'),
                        ('no_media', 'No Media Available'),
                    ],
                    max_length=20,
                )),
                ('fb_post_id', models.CharField(blank=True, max_length=100)),
                ('caption_used', models.TextField(blank=True)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('config', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='post_logs',
                    to='automation.autopostconfig',
                )),
                ('media', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='automation.cloudmediamanager',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
