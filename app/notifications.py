
def create_follow_notification(follower_id, followed_id):
    follower = User.query.filter_by(id=follower_id).first()
    notification = Notification(
        user_id=followed_id,
        sender_id=follower_id,
        sender = follower,
        type='follow',
        content=f'{follower.username} followed you.'
    )
    db.session.add(notification)
    db.session.commit()

def create_like_notification(sender_id, recipient_id, post_id):
    liker = User.query.filter_by(id=sender_id).first()
    notification = Notification(
        user_id=recipient_id,
        sender_id=sender_id,
        sender = liker,
        type='like',
        content=f'{liker.username} liked your post {post_id}.'
    )
    db.session.add(notification)
    db.session.commit()



