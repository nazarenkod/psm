from aifashion.core.models import PhotoRole
from aifashion.core.photo_retention import RetentionAction, retention_action


def test_selfie_kept():
    assert retention_action(PhotoRole.selfie) is RetentionAction.keep


def test_flat_lay_is_canonical_item_photo():
    assert retention_action(PhotoRole.flat_lay) is RetentionAction.keep_canonical


def test_product_and_reference_deleted_after_extract():
    assert retention_action(PhotoRole.product_shot) is RetentionAction.delete_after_extract
    assert retention_action(PhotoRole.outfit_reference) is RetentionAction.delete_after_extract
