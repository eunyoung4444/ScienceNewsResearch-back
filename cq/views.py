import itertools
from functools import reduce

from django.http import JsonResponse
from django.utils.timezone import now

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework.response import Response as HTTPResponse
from rest_framework import permissions, viewsets, status
from cq.permission import CustomProfilePermission, CustomUserPermission
from rest_framework.decorators import detail_route
from rest_framework_extensions.mixins import NestedViewSetMixin

from cq.models import Research, Article, Sentence, Question, Take, Response, Milestone, Profile
from cq.serializers import UserSerializer, ResearchSerializer, ArticleSerializer, QuestionSerializer, \
    SentenceSerializer, TakeSerializer, ResponseSerializer, TakeBindMilestoneSerializer, MileStoneSerializer, \
    ProfileSerializer


class ResearchViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Research.objects.all()
    serializer_class = ResearchSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(
            author=self.request.data.get('author'),
            title=self.request.data.get('title')
        )


class ArticleViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = (permissions.IsAuthenticated,)


class QuestionViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    pagination_class = None
    serializer_class = QuestionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        queryset = Question.objects.all()
        created_phase = self.request.query_params.get('created_phase', None)
        if created_phase is not None:
            queryset = queryset.filter(created_phase=created_phase)
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class SentenceViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Sentence.objects.all()
    serializer_class = SentenceSerializer
    permission_classes = (permissions.IsAuthenticated,)


class TakeBindMilestoneViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    pagination_class = None
    queryset = Take.objects.all()
    serializer_class = TakeBindMilestoneSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_update(self, serializer):
        is_removed = self.request.data.get('remove')
        if is_removed:
            serializer.save(removed_at=now())
        else:
            serializer.save()

    @detail_route(methods=['patch'])
    def renew_milestone(self, request, pk=None):

        # will receive take_id, sentence_id(Many)
        take = self.get_object()
        sentences = request.data.pop('sentences', [])

        # create new milestone
        request.data.update(take=take.id)
        m_serializer = MileStoneSerializer(data=request.data)
        m_serializer.is_valid(raise_exception=True)
        milestone = m_serializer.save(user=self.request.user)

        # save highlights(Response)
        response_form = []
        for sentence_id in sentences:
            response_form.append({
                'take': take.id,
                'milestone': m_serializer.data.get('id'),
                'sentence': sentence_id,
            })
        r_serializer = ResponseSerializer(data=response_form, many=True)
        r_serializer.is_valid(raise_exception=True)
        r_serializer.save(user=self.request.user)

        serializer = MileStoneSerializer(milestone, data={'take': take.id, 'responses': r_serializer})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return HTTPResponse(serializer.data)

    @detail_route(methods=['get'])
    def suggestions(self, request, pk=None):
        take = self.get_object()
        related_takes = Take.objects\
            .exclude(article=take.article)\
            .filter(question=take.question)
        query_set = list(related_takes)
        milestones = list(map(lambda x: list(x.milestones.filter(copied_from=None).exclude(found=None).exclude(responses=None)), query_set))
        milestones_flatten = list(itertools.chain.from_iterable(milestones))
        latest_milestone = None if len(milestones_flatten) is 0 \
            else reduce(lambda x, y: y if x.response_at < y.response_at else x, milestones_flatten)
        if latest_milestone is None:
            responses = Response.objects.none()
        else:
            responses = latest_milestone.responses
        return HTTPResponse(ResponseSerializer(responses, many=True).data)


class TakeViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Take.objects.all()
    serializer_class = TakeSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
        )


class ResponseViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Response.objects.all()
    serializer_class = ResponseSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
        )


class MilestoneViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Milestone.objects.all()
    serializer_class = MileStoneSerializer
    permission_classes = (permissions.IsAuthenticated,)


class UserViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (CustomUserPermission,)
    lookup_field = 'username'

    def create(self, request, *args, **kwargs):
        research_id = request.data.pop('research', None)
        research = Research.objects.filter(pk=research_id)
        if not research.exists():
            return JsonResponse({'non_field_errors': ['Select any research type.']}, status=400)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        profile = instance.profile
        if research_id is not None:
            articles = Article.objects.filter(research=research)
            target_article = reduce(lambda x, y: y if x.profiles.count() > y.profiles.count() else x, articles)
            p_serializer = ProfileSerializer(profile, data={
                'article': target_article.id,
                'user': instance.id
            })
            p_serializer.is_valid(raise_exception=True)
            p_serializer.save()

        return HTTPResponse(serializer.data)

    def list(self, request, *args, **kwargs):
        if self.request.user.is_superuser:
            queryset = User.objects.all()
        else:
            queryset = User.objects.filter(username=self.request.user)
        serializer = UserSerializer(queryset, many=True)
        return HTTPResponse(serializer.data)


class ProfileViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = (CustomProfilePermission,)

