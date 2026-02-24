"""
Study Groups API Endpoints for AI Study System

Provides REST API endpoints for managing collaborative study groups,
group membership, and shared study materials.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import json

from .auth_api import get_current_user_dependency
from kb.auth_utils import UserCredentials
from kb.metadata_db import MetadataDB

# Initialize router and security
router = APIRouter(prefix="/api/groups", tags=["study-groups"])
security = HTTPBearer()

# Pydantic models for request/response
class StudyGroupCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = True

class StudyGroupUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None

class StudyGroupResponse(BaseModel):
    group_id: int
    name: str
    description: Optional[str] = None
    is_public: bool
    created_by: int
    created_at: str
    member_count: int

class GroupMemberResponse(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: Optional[str] = None
    joined_at: str
    role: str  # 'owner', 'member'

class SharedMaterialResponse(BaseModel):
    share_id: int
    material_id: int
    material_title: str
    material_type: str
    shared_by: int
    shared_by_username: str
    shared_at: str
    access_level: str  # 'read', 'write'

class InviteUserRequest(BaseModel):
    email: EmailStr

class MessageResponse(BaseModel):
    message: str


@router.post("", response_model=StudyGroupResponse)
async def create_study_group(
    request: StudyGroupCreateRequest,
    current_user: UserCredentials = Depends(get_current_user_dependency)
):
    """
    Create a new study group.

    The creator automatically becomes the owner of the group.
    """
    try:
        # Initialize database
        db = MetadataDB()

        # Create study group
        group_id = db.create_study_group(
            name=request.name,
            description=request.description,
            created_by=current_user.user_id,
            is_public=request.is_public
        )

        # Get created group data with member count
        group_data = db.get_study_group_by_id(group_id)
        if not group_data:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve created group"
            )

        return StudyGroupResponse(
            group_id=group_data['group_id'],
            name=group_data['name'],
            description=group_data.get('description'),
            is_public=bool(group_data['is_public']),
            created_by=group_data['created_by'],
            created_at=group_data['created_at'],
            member_count=1  # Creator is the first member
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create group: {str(e)}")


@router.get("", response_model=List[StudyGroupResponse])
async def get_user_groups(
    current_user: UserCredentials = Depends(get_current_user_dependency),
    include_public: bool = Query(True, description="Include public groups user can join")
):
    """
    Get all study groups for the current user.

    Includes groups where the user is a member, and optionally public groups.
    """
    try:
        # Initialize database
        db = MetadataDB()

        # Get user's groups
        groups = db.get_user_study_groups(current_user.user_id, include_public)

        return [
            StudyGroupResponse(
                group_id=group['group_id'],
                name=group['name'],
                description=group.get('description'),
                is_public=bool(group['is_public']),
                created_by=group['created_by'],
                created_at=group['created_at'],
                member_count=group['member_count']
            )
            for group in groups
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get groups: {str(e)}")


@router.get("/{group_id}", response_model=StudyGroupResponse)
async def get_study_group(
    group_id: int,
    current_user: UserCredentials = Depends(get_current_user_dependency)
):
    """
    Get details of a specific study group.

    User must be a member of the group or the group must be public.
    """
    try:
        # Initialize database
        db = MetadataDB()

        # Check if user has access to the group
        if not db.user_can_access_group(current_user.user_id, group_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied to this study group"
            )

        # Get group data
        group_data = db.get_study_group_by_id(group_id)
        if not group_data:
            raise HTTPException(status_code=404, detail="Study group not found")

        # Get member count
        member_count = db.get_group_member_count(group_id)

        return StudyGroupResponse(
            group_id=group_data['group_id'],
            name=group_data['name'],
            description=group_data.get('description'),
            is_public=bool(group_data['is_public']),
            created_by=group_data['created_by'],
            created_at=group_data['created_at'],
            member_count=member_count
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get group: {str(e)}")


@router.put("/{group_id}", response_model=StudyGroupResponse)
async def update_study_group(
    group_id: int,
    request: StudyGroupUpdateRequest,
    current_user: UserCredentials = Depends(get_current_user_dependency)
):
    """
    Update a study group's information.

    Only the group owner can update the group.
    """
    try:
        # Initialize database
        db = MetadataDB()

        # Check if user is the owner
        group_data = db.get_study_group_by_id(group_id)
        if not group_data:
            raise HTTPException(status_code=404, detail="Study group not found")

        if group_data['created_by'] != current_user.user_id:
            raise HTTPException(
                status_code=403,
                detail="Only group owner can update group information"
            )

        # Update group
        db.update_study_group(
            group_id=group_id,
            name=request.name,
            description=request.description,
            is_public=request.is_public
        )

        # Get updated group data
        updated_group = db.get_study_group_by_id(group_id)
        member_count = db.get_group_member_count(group_id)

        return StudyGroupResponse(
            group_id=updated_group['group_id'],
            name=updated_group['name'],
            description=updated_group.get('description'),
            is_public=bool(updated_group['is_public']),
            created_by=updated_group['created_by'],
            created_at=updated_group['created_at'],
            member_count=member_count
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update group: {str(e)}")


@router.delete("/{group_id}", response_model=MessageResponse)
async def delete_study_group(
    group_id: int,
    current_user: UserCredentials = Depends(get_current_user_dependency)
):
    """
    Delete a study group.

    Only the group owner can delete the group.
    """
    try:
        # Initialize database
        db = MetadataDB()

        # Check if user is the owner
        group_data = db.get_study_group_by_id(group_id)
        if not group_data:
            raise HTTPException(status_code=404, detail="Study group not found")

        if group_data['created_by'] != current_user.user_id:
            raise HTTPException(
                status_code=403,
                detail="Only group owner can delete the group"
            )

        # Delete group
        db.delete_study_group(group_id)

        return MessageResponse(message="Study group deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete group: {str(e)}")


@router.post("/{group_id}/join", response_model=MessageResponse)
async def join_study_group(
    group_id: int,
    current_user: UserCredentials = Depends(get_current_user_dependency)
):
    """
    Join a study group.

    User can join public groups or private groups if invited.
    """
    try:
        # Initialize database
        db = MetadataDB()

        # Check if group exists and is accessible
        group_data = db.get_study_group_by_id(group_id)
        if not group_data:
            raise HTTPException(status_code=404, detail="Study group not found")

        # Check if user is already a member
        if db.is_user_in_group(current_user.user_id, group_id):
            raise HTTPException(
                status_code=400,
                detail="User is already a member of this group"
            )

        # Join the group
        db.join_study_group(current_user.user_id, group_id)

        return MessageResponse(message="Successfully joined the study group")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to join group: {str(e)}")


@router.post("/{group_id}/leave", response_model=MessageResponse)
async def leave_study_group(
    group_id: int,
    current_user: UserCredentials = Depends(get_current_user_dependency)
):
    """
    Leave a study group.

    Group owners cannot leave their own groups.
    """
    try:
        # Initialize database
        db = MetadataDB()

        # Check if group exists
        group_data = db.get_study_group_by_id(group_id)
        if not group_data:
            raise HTTPException(status_code=404, detail="Study group not found")

        # Check if user is the owner
        if group_data['created_by'] == current_user.user_id:
            raise HTTPException(
                status_code=400,
                detail="Group owner cannot leave the group"
            )

        # Check if user is a member
        if not db.is_user_in_group(current_user.user_id, group_id):
            raise HTTPException(
                status_code=400,
                detail="User is not a member of this group"
            )

        # Leave the group
        db.leave_study_group(current_user.user_id, group_id)

        return MessageResponse(message="Successfully left the study group")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to leave group: {str(e)}")


@router.get("/{group_id}/members", response_model=List[GroupMemberResponse])
async def get_group_members(
    group_id: int,
    current_user: UserCredentials = Depends(get_current_user_dependency)
):
    """
    Get all members of a study group.

    User must be a member of the group.
    """
    try:
        # Initialize database
        db = MetadataDB()

        # Check if user has access to the group
        if not db.user_can_access_group(current_user.user_id, group_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied to this study group"
            )

        # Get group members
        members = db.get_group_members(group_id)

        return [
            GroupMemberResponse(
                user_id=member['user_id'],
                username=member['username'],
                email=member['email'],
                full_name=member.get('full_name'),
                joined_at=member['joined_at'],
                role=member['role']
            )
            for member in members
        ]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get group members: {str(e)}")


@router.post("/{group_id}/materials/{material_id}/share", response_model=MessageResponse)
async def share_material_with_group(
    group_id: int,
    material_id: int,
    access_level: str = Query("read", regex="^(read|write)$"),
    current_user: UserCredentials = Depends(get_current_user_dependency)
):
    """
    Share a study material with a study group.

    User must be a member of the group and have access to the material.
    """
    try:
        # Initialize database
        db = MetadataDB()

        # Check if user has access to the group
        if not db.user_can_access_group(current_user.user_id, group_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied to this study group"
            )

        # Check if material exists and user has access
        material = db.get_study_material(material_id)
        if not material:
            raise HTTPException(status_code=404, detail="Study material not found")

        if material['created_by'] != current_user.user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to this study material"
            )

        # Share the material
        db.share_material_with_group(
            material_id=material_id,
            group_id=group_id,
            shared_by=current_user.user_id,
            access_level=access_level
        )

        return MessageResponse(message="Material shared with group successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to share material: {str(e)}")


@router.get("/{group_id}/materials", response_model=List[SharedMaterialResponse])
async def get_group_shared_materials(
    group_id: int,
    current_user: UserCredentials = Depends(get_current_user_dependency)
):
    """
    Get all materials shared with a study group.

    User must be a member of the group.
    """
    try:
        # Initialize database
        db = MetadataDB()

        # Check if user has access to the group
        if not db.user_can_access_group(current_user.user_id, group_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied to this study group"
            )

        # Get shared materials
        materials = db.get_group_shared_materials(group_id)

        return [
            SharedMaterialResponse(
                share_id=material['share_id'],
                material_id=material['material_id'],
                material_title=material['title'],
                material_type=material['material_type'],
                shared_by=material['shared_by'],
                shared_by_username=material['shared_by_username'],
                shared_at=material['shared_at'],
                access_level=material['access_level']
            )
            for material in materials
        ]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get shared materials: {str(e)}")


@router.delete("/{group_id}/materials/{material_id}/share", response_model=MessageResponse)
async def unshare_material_from_group(
    group_id: int,
    material_id: int,
    current_user: UserCredentials = Depends(get_current_user_dependency)
):
    """
    Remove a shared material from a study group.

    Only the person who shared the material can unshare it.
    """
    try:
        # Initialize database
        db = MetadataDB()

        # Check if user has access to the group
        if not db.user_can_access_group(current_user.user_id, group_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied to this study group"
            )

        # Unshare the material
        db.unshare_material_from_group(
            material_id=material_id,
            group_id=group_id,
            shared_by=current_user.user_id
        )

        return MessageResponse(message="Material unshared from group successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unshare material: {str(e)}")