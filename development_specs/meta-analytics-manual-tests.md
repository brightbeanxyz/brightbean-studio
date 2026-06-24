# Meta Analytics Manual Test Plan

Use a Page/Instagram account that has granted the analytics scopes and replace
IDs/tokens with real values.

## Facebook Page

```text
/{page_id}/insights?metric=page_media_view,page_total_media_view_unique,page_follows,page_post_engagements&period=day&since={since}&until={until}
```

## Facebook Post

```text
/{facebook_post_id}/insights?metric=post_media_view,post_total_media_view_unique,post_clicks,post_reactions_by_type_total
```

## Facebook Post Fields

```text
/{facebook_post_id}?fields=id,message,created_time,permalink_url,full_picture,shares,comments.limit(0).summary(true),reactions.limit(0).summary(true)
```

## Instagram User

```text
/{ig_user_id}?fields=id,username,name,profile_picture_url,followers_count,media_count
```

## Instagram Account Insights

```text
/{ig_user_id}/insights?metric=reach,views,accounts_engaged,total_interactions&period=day&since={since}&until={until}
```

## Instagram Media Fields

```text
/{ig_user_id}/media?fields=id,caption,media_type,media_product_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count
```

## Instagram Media Insights

```text
/{ig_media_id}/insights?metric=reach,views,likes,comments,saved,shares,total_interactions
```

Expected UI checks:

- Facebook shows Views, not Impressions.
- Facebook uses Reactions, not Likes.
- Instagram shows Views.
- Engagement rate is 0 when views and reach are 0.
- Unsupported metrics log warnings and do not stop the dashboard from loading.
- 7D, 30D, and 90D filters update totals and chart data.
- Instagram follower growth derives from the profile `followers_count` total (the deprecated
  `profile_views` insight is no longer requested, so no per-sync warning for it).
