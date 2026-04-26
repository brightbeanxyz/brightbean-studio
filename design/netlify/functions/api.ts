import crypto from "node:crypto";
import { createClient } from "@supabase/supabase-js";

type Event = {
  path: string;
  httpMethod: string;
  headers: Record<string, string | undefined>;
  body: string | null;
  rawQuery?: string;
  queryStringParameters?: Record<string, string | undefined>;
};

type AccountRow = {
  id: string;
  workspace_id: string;
  channel_group_id: string | null;
  connected_by?: string | null;
  platform: "facebook" | "youtube" | "tiktok";
  account_platform_id: string;
  account_name: string;
  account_handle: string;
  avatar_url: string;
  follower_count: number;
  connection_status: string;
  last_error: string;
  last_health_check_at: string | null;
  metadata?: Record<string, unknown>;
};

type WorkspaceContext = {
  workspace: { id: string; name: string; slug: string };
  membership: { id: string; role: string };
};

const env = {
  supabaseUrl: process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || "",
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY || process.env.VITE_SUPABASE_ANON_KEY || "",
  supabaseServiceRoleKey: process.env.SUPABASE_SERVICE_ROLE_KEY || "",
  appUrl: (process.env.APP_URL || "").replace(/\/+$/, ""),
  appStateSecret: process.env.APP_STATE_SECRET || "",
  cronSecret: process.env.CRON_SECRET || "",
  facebookAppId: process.env.PLATFORM_FACEBOOK_APP_ID || "",
  facebookAppSecret: process.env.PLATFORM_FACEBOOK_APP_SECRET || "",
  googleClientId: process.env.PLATFORM_GOOGLE_CLIENT_ID || "",
  googleClientSecret: process.env.PLATFORM_GOOGLE_CLIENT_SECRET || "",
  tiktokClientKey: process.env.PLATFORM_TIKTOK_CLIENT_KEY || "",
  tiktokClientSecret: process.env.PLATFORM_TIKTOK_CLIENT_SECRET || "",
};

function response(statusCode: number, body: unknown, headers: Record<string, string> = {}) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      ...headers,
    },
    body: JSON.stringify(body),
  };
}

function redirect(location: string) {
  return {
    statusCode: 302,
    headers: {
      Location: location,
      "Cache-Control": "no-store",
    },
    body: "",
  };
}

function oauthRedirect(location: string) {
  return response(200, { redirect: location });
}

function compactNumber(value: number | null | undefined) {
  const safe = Number(value || 0);
  if (safe >= 1_000_000) return `${(safe / 1_000_000).toFixed(1)}M`;
  if (safe >= 1_000) return `${(safe / 1_000).toFixed(1)}K`;
  return String(Math.round(safe));
}

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 50);
}

function parseBody(event: Event) {
  if (!event.body) return {};
  try {
    return JSON.parse(event.body);
  } catch {
    return {};
  }
}

function getPath(event: Event) {
  return event.path.replace(/^\/\.netlify\/functions\/api/, "").replace(/^\/api/, "") || "/";
}

function queryValue(event: Event, key: string) {
  if (event.queryStringParameters?.[key]) return event.queryStringParameters[key] || "";
  const raw = event.rawQuery || "";
  const params = new URLSearchParams(raw.startsWith("?") ? raw.slice(1) : raw);
  return params.get(key) || "";
}

function createPublicClient() {
  return createClient(env.supabaseUrl, env.supabaseAnonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

function createAdminClient() {
  return createClient(env.supabaseUrl, env.supabaseServiceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

function normalizeUsername(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 32);
}

function isEmail(value: string) {
  return /\S+@\S+\.\S+/.test(value);
}

function internalEmailForUsername(username: string) {
  return `${normalizeUsername(username)}@users.local`;
}

async function resolveIdentifierToEmail(admin: ReturnType<typeof createAdminClient>, identifier: string) {
  const trimmed = String(identifier || "").trim().toLowerCase();
  if (!trimmed) return "";
  if (isEmail(trimmed)) return trimmed;

  const normalized = normalizeUsername(trimmed);
  const { data: profiles } = await admin.from("profiles").select("email, username").limit(500);
  const match = (profiles || []).find((profile: any) => {
    const username = String(profile.username || "").trim().toLowerCase();
    const email = String(profile.email || "").trim().toLowerCase();
    return username === normalized || email === trimmed || email.startsWith(`${trimmed}@`);
  }) as any;

  if (match?.email) return String(match.email).trim().toLowerCase();
  return internalEmailForUsername(trimmed);
}

async function handleAuthSignIn(event: Event, admin: ReturnType<typeof createAdminClient>) {
  const body = parseBody(event);
  const identifier = String(body.identifier || body.username || body.email || "").trim();
  const password = String(body.password || "");

  if (!identifier || !password) {
    return response(400, { error: "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu." });
  }

  const email = await resolveIdentifierToEmail(admin, identifier);
  const client = createPublicClient();
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  if (error || !data.session || !data.user) {
    return response(401, { error: "Sai tên đăng nhập hoặc mật khẩu." });
  }

  await ensureWorkspaceForUser(admin, data.user);

  return response(200, {
    session: {
      access_token: data.session.access_token,
      refresh_token: data.session.refresh_token,
      expires_at: data.session.expires_at,
      expires_in: data.session.expires_in,
      token_type: data.session.token_type,
      user: data.user,
    },
  });
}

async function handleAuthSignUp(event: Event, admin: ReturnType<typeof createAdminClient>) {
  const body = parseBody(event);
  const name = String(body.name || "").trim();
  const username = normalizeUsername(String(body.username || ""));
  const password = String(body.password || "");
  const email = String(body.email || "").trim().toLowerCase() || internalEmailForUsername(username);

  if (!name || !username || !password) {
    return response(400, { error: "Vui lòng nhập đầy đủ họ tên, tên đăng nhập và mật khẩu." });
  }

  const { data: existingProfiles } = await admin.from("profiles").select("email, username").limit(500);
  const duplicated = (existingProfiles || []).find((profile: any) => {
    const existingUsername = String(profile.username || "").trim().toLowerCase();
    const existingEmail = String(profile.email || "").trim().toLowerCase();
    return existingUsername === username || existingEmail === email;
  });
  if (duplicated) {
    return response(400, { error: "Tên đăng nhập hoặc email đã tồn tại." });
  }

  const created = await admin.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
    user_metadata: {
      full_name: name,
      username,
    },
  });

  if (created.error || !created.data.user) {
    return response(400, { error: created.error?.message || "Không thể tạo tài khoản." });
  }

  await admin
    .from("profiles")
    .upsert({ id: created.data.user.id, email, full_name: name, username }, { onConflict: "id" });

  await ensureWorkspaceForUser(admin, created.data.user);

  const client = createPublicClient();
  const signedIn = await client.auth.signInWithPassword({ email, password });
  if (signedIn.error || !signedIn.data.session || !signedIn.data.user) {
    return response(201, { ok: true });
  }

  return response(201, {
    session: {
      access_token: signedIn.data.session.access_token,
      refresh_token: signedIn.data.session.refresh_token,
      expires_at: signedIn.data.session.expires_at,
      expires_in: signedIn.data.session.expires_in,
      token_type: signedIn.data.session.token_type,
      user: signedIn.data.user,
    },
  });
}

async function getCurrentUser(event: Event) {
  const authorization = event.headers.authorization || event.headers.Authorization;
  if (!authorization || !authorization.startsWith("Bearer ")) {
    return null;
  }
  const client = createClient(env.supabaseUrl, env.supabaseAnonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { headers: { Authorization: authorization } },
  });
  const { data, error } = await client.auth.getUser();
  if (error || !data.user) return null;
  return data.user;
}

function signedState(payload: Record<string, string>) {
  const data = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = crypto.createHmac("sha256", env.appStateSecret).update(data).digest("base64url");
  return `${data}.${signature}`;
}

function verifyState(value: string) {
  const [data, signature] = value.split(".");
  if (!data || !signature) throw new Error("Invalid state");
  const expected = crypto.createHmac("sha256", env.appStateSecret).update(data).digest("base64url");
  if (signature !== expected) throw new Error("Invalid state signature");
  const payload = JSON.parse(Buffer.from(data, "base64url").toString("utf8"));
  if (!payload.ts || Date.now() - Number(payload.ts) > 10 * 60 * 1000) {
    throw new Error("Expired state");
  }
  return payload as Record<string, string>;
}

async function ensureWorkspaceForUser(admin: ReturnType<typeof createAdminClient>, user: any): Promise<WorkspaceContext> {
  const { data: membershipRows, error: membershipError } = await admin
    .from("workspace_members")
    .select("id, role, workspace:workspaces(id, name, slug)")
    .eq("user_id", user.id)
    .limit(1);

  if (membershipError) throw membershipError;
  if (membershipRows && membershipRows.length > 0) {
    const row = membershipRows[0] as any;
    return {
      workspace: row.workspace,
      membership: { id: row.id, role: row.role },
    };
  }

  const baseName =
    user.user_metadata?.workspace_name ||
    user.user_metadata?.full_name ||
    user.email?.split("@")[0] ||
    "Workspace";
  const workspaceName = `${baseName} Workspace`;
  const slugBase = slugify(workspaceName) || "workspace";

  const { data: workspace, error: workspaceError } = await admin
    .from("workspaces")
    .insert({
      name: workspaceName,
      slug: `${slugBase}-${crypto.randomBytes(3).toString("hex")}`,
      owner_user_id: user.id,
    })
    .select("id, name, slug")
    .single();

  if (workspaceError || !workspace) throw workspaceError || new Error("Failed to create workspace");

  const { data: membership, error: createMembershipError } = await admin
    .from("workspace_members")
    .insert({
      workspace_id: workspace.id,
      user_id: user.id,
      role: "owner",
    })
    .select("id, role")
    .single();

  if (createMembershipError || !membership) throw createMembershipError || new Error("Failed to create workspace membership");

  await admin.from("channel_groups").insert([
    { workspace_id: workspace.id, name: "Tất cả kênh", position: 0, is_favorite: true },
    { workspace_id: workspace.id, name: "Thương hiệu", position: 1 },
    { workspace_id: workspace.id, name: "Campaign", position: 2 },
  ]);

  await admin.from("user_settings").upsert({ user_id: user.id });

  return {
    workspace,
    membership,
  };
}

async function getWorkspaceMembership(
  admin: ReturnType<typeof createAdminClient>,
  workspaceId: string,
  userId: string,
) {
  const { data, error } = await admin
    .from("workspace_members")
    .select("id, role, workspace:workspaces(id, name, slug)")
    .eq("workspace_id", workspaceId)
    .eq("user_id", userId)
    .single();

  if (error || !data) return null;
  return data as any;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error((json as any).error?.message || (json as any).error_description || `Request failed: ${response.status}`);
  }
  return json as T;
}

async function upsertAccount(
  admin: ReturnType<typeof createAdminClient>,
  account: {
    workspaceId: string;
    channelGroupId?: string | null;
    connectedBy: string;
    platform: "facebook" | "youtube" | "tiktok";
    platformId: string;
    name: string;
    handle?: string;
    avatarUrl?: string;
    followers?: number;
    status?: string;
    metadata?: Record<string, unknown>;
  },
) {
  const { data, error } = await admin
    .from("social_accounts")
    .upsert(
      {
        workspace_id: account.workspaceId,
        channel_group_id: account.channelGroupId || null,
        connected_by: account.connectedBy,
        platform: account.platform,
        account_platform_id: account.platformId,
        account_name: account.name,
        account_handle: account.handle || "",
        avatar_url: account.avatarUrl || "",
        follower_count: Math.max(0, Number(account.followers || 0)),
        connection_status: account.status || "connected",
        metadata: account.metadata || {},
      },
      { onConflict: "workspace_id,platform,account_platform_id" },
    )
    .select("*")
    .single();

  if (error || !data) throw error || new Error("Failed to upsert account");
  return data as AccountRow;
}

async function saveTokens(
  admin: ReturnType<typeof createAdminClient>,
  socialAccountId: string,
  tokens: {
    accessToken: string;
    refreshToken?: string;
    expiresIn?: number | null;
    scope?: string;
    metadata?: Record<string, unknown>;
  },
) {
  const tokenExpiresAt =
    tokens.expiresIn && Number(tokens.expiresIn) > 0
      ? new Date(Date.now() + Number(tokens.expiresIn) * 1000).toISOString()
      : null;

  const { error } = await admin.from("social_account_tokens").upsert({
    social_account_id: socialAccountId,
    access_token: tokens.accessToken,
    refresh_token: tokens.refreshToken || "",
    token_expires_at: tokenExpiresAt,
    scope: tokens.scope || "",
    token_metadata: tokens.metadata || {},
  });

  if (error) throw error;
}

async function getTokens(admin: ReturnType<typeof createAdminClient>, socialAccountId: string) {
  const { data, error } = await admin
    .from("social_account_tokens")
    .select("*")
    .eq("social_account_id", socialAccountId)
    .single();

  if (error || !data) throw error || new Error("Missing token");
  return data as any;
}

function tokenExpiresSoon(token: any) {
  if (!token?.token_expires_at) return false;
  return new Date(token.token_expires_at).getTime() <= Date.now() + 5 * 60 * 1000;
}

function tokenExpiresWithin(token: any, ms: number) {
  if (!token?.token_expires_at) return false;
  return new Date(token.token_expires_at).getTime() <= Date.now() + ms;
}

function isReconnectError(message: string) {
  const value = String(message || "").toLowerCase();
  return [
    "token",
    "oauth",
    "auth",
    "expired",
    "unauthorized",
    "permission",
    "invalid grant",
    "invalid_credentials",
    "access denied",
    "login",
    "reconnect",
  ].some((part) => value.includes(part));
}

function describeTokenHealth(account: AccountRow, token: any) {
  const expiresAt = token?.token_expires_at || null;
  const hasRefreshToken = Boolean(token?.refresh_token);
  const reconnectRequired = account.connection_status !== "connected" || isReconnectError(account.last_error || "");

  if (!token?.access_token) {
    return {
      status: "missing",
      label: "Thiếu token",
      severity: "error",
      reconnectRequired: true,
      hasRefreshToken,
      expiresAt,
      description: "Kênh chưa có access token hợp lệ.",
    };
  }

  if (expiresAt && new Date(expiresAt).getTime() <= Date.now()) {
    return {
      status: hasRefreshToken ? "expired_refreshable" : "expired",
      label: hasRefreshToken ? "Đã hết hạn, có thể tự làm mới" : "Đã hết hạn",
      severity: hasRefreshToken ? "warning" : "error",
      reconnectRequired: !hasRefreshToken || reconnectRequired,
      hasRefreshToken,
      expiresAt,
      description: hasRefreshToken ? "Hệ thống sẽ thử tự làm mới token ở lần đồng bộ kế tiếp." : "Token đã hết hạn và cần kết nối lại.",
    };
  }

  if (tokenExpiresWithin(token, 24 * 60 * 60 * 1000)) {
    return {
      status: hasRefreshToken ? "expiring_refreshable" : "expiring",
      label: hasRefreshToken ? "Sắp hết hạn, có thể tự làm mới" : "Sắp hết hạn",
      severity: hasRefreshToken ? "warning" : "error",
      reconnectRequired: !hasRefreshToken,
      hasRefreshToken,
      expiresAt,
      description: hasRefreshToken ? "Token sẽ được tự làm mới khi cần." : "Token sắp hết hạn nhưng không có refresh token.",
    };
  }

  if (reconnectRequired) {
    return {
      status: "reconnect_required",
      label: "Cần kết nối lại",
      severity: "error",
      reconnectRequired: true,
      hasRefreshToken,
      expiresAt,
      description: account.last_error || "Phiên kết nối không còn ổn định.",
    };
  }

  if (!expiresAt) {
    return {
      status: hasRefreshToken ? "healthy_refreshable" : "healthy",
      label: hasRefreshToken ? "Ổn định, có refresh token" : "Ổn định",
      severity: "success",
      reconnectRequired: false,
      hasRefreshToken,
      expiresAt,
      description: hasRefreshToken ? "Kênh đang hoạt động và có thể tự làm mới token." : "Kênh đang hoạt động ổn định.",
    };
  }

  return {
    status: hasRefreshToken ? "healthy_refreshable" : "healthy",
    label: hasRefreshToken ? "Ổn định, có refresh token" : "Ổn định",
    severity: "success",
    reconnectRequired: false,
    hasRefreshToken,
    expiresAt,
    description: "Kênh đang hoạt động ổn định.",
  };
}

function parseGrantedScopes(scopeValue?: string | null) {
  if (!scopeValue) return [] as string[];
  return Array.from(
    new Set(
      scopeValue
        .split(/[\s,]+/)
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  );
}

function requiredScopesForPlatform(platform: string) {
  if (platform === "facebook") return facebookScopes();
  if (platform === "youtube") return youtubeScopes();
  if (platform === "tiktok") return tiktokScopes();
  return [] as string[];
}

async function refreshGoogleToken(admin: ReturnType<typeof createAdminClient>, socialAccountId: string, tokens: any) {
  if (!tokens.refresh_token) return tokens;
  const tokenBody = new URLSearchParams({
    client_id: env.googleClientId,
    client_secret: env.googleClientSecret,
    refresh_token: tokens.refresh_token,
    grant_type: "refresh_token",
  });
  const refreshed = await fetchJson<any>("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: tokenBody.toString(),
  });
  const nextTokens = {
    ...tokens,
    access_token: refreshed.access_token,
    refresh_token: refreshed.refresh_token || tokens.refresh_token,
    scope: refreshed.scope || tokens.scope,
    token_metadata: refreshed,
  };
  await saveTokens(admin, socialAccountId, {
    accessToken: nextTokens.access_token,
    refreshToken: nextTokens.refresh_token,
    expiresIn: refreshed.expires_in,
    scope: nextTokens.scope,
    metadata: nextTokens.token_metadata,
  });
  return {
    ...nextTokens,
    token_expires_at: refreshed.expires_in ? new Date(Date.now() + Number(refreshed.expires_in) * 1000).toISOString() : tokens.token_expires_at,
  };
}

async function refreshTikTokToken(admin: ReturnType<typeof createAdminClient>, socialAccountId: string, tokens: any) {
  if (!tokens.refresh_token) return tokens;
  const tokenBody = new URLSearchParams({
    client_key: env.tiktokClientKey,
    client_secret: env.tiktokClientSecret,
    refresh_token: tokens.refresh_token,
    grant_type: "refresh_token",
  });
  const refreshed = await fetchJson<any>("https://open.tiktokapis.com/v2/oauth/token/", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: tokenBody.toString(),
  });
  const nextTokens = {
    ...tokens,
    access_token: refreshed.access_token,
    refresh_token: refreshed.refresh_token || tokens.refresh_token,
    scope: refreshed.scope || tokens.scope,
    token_metadata: refreshed,
  };
  await saveTokens(admin, socialAccountId, {
    accessToken: nextTokens.access_token,
    refreshToken: nextTokens.refresh_token,
    expiresIn: refreshed.expires_in,
    scope: nextTokens.scope,
    metadata: nextTokens.token_metadata,
  });
  return {
    ...nextTokens,
    token_expires_at: refreshed.expires_in ? new Date(Date.now() + Number(refreshed.expires_in) * 1000).toISOString() : tokens.token_expires_at,
  };
}

async function ensureFreshTokens(admin: ReturnType<typeof createAdminClient>, account: AccountRow, tokens: any) {
  if (!tokenExpiresSoon(tokens)) return tokens;
  if (account.platform === "youtube") {
    return refreshGoogleToken(admin, account.id, tokens);
  }
  if (account.platform === "tiktok") {
    return refreshTikTokToken(admin, account.id, tokens);
  }
  return tokens;
}

async function markAccountSyncFailure(admin: ReturnType<typeof createAdminClient>, accountId: string, errorMessage: string) {
  await admin
    .from("social_accounts")
    .update({
      connection_status: "error",
      last_error: errorMessage || "Sync failed",
      last_health_check_at: new Date().toISOString(),
    })
    .eq("id", accountId);
}

function buildOAuthAuthorizeUrl(platform: "facebook" | "youtube" | "tiktok", state: string) {
  const redirectUri = `${env.appUrl}/api/oauth/callback/${platform}`;

  if (platform === "facebook") {
    const params = new URLSearchParams({
      client_id: env.facebookAppId,
      redirect_uri: redirectUri,
      state,
      response_type: "code",
      scope: facebookScopes().join(","),
    });
    return `https://www.facebook.com/v20.0/dialog/oauth?${params.toString()}`;
  }

  if (platform === "youtube") {
    const params = new URLSearchParams({
      client_id: env.googleClientId,
      redirect_uri: redirectUri,
      state,
      scope: youtubeScopes().join(" "),
      response_type: "code",
      access_type: "offline",
      prompt: "consent",
    });
    return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
  }

  const params = new URLSearchParams({
    client_key: env.tiktokClientKey,
    redirect_uri: redirectUri,
    state,
    scope: tiktokScopes().join(","),
    response_type: "code",
  });
  return `https://www.tiktok.com/v2/auth/authorize/?${params.toString()}`;
}

async function upsertDailyMetrics(
  admin: ReturnType<typeof createAdminClient>,
  workspaceId: string,
  socialAccountId: string,
  rows: Array<Record<string, unknown>>,
) {
  if (!rows.length) return;
  const payload = rows.map((row) => ({
    workspace_id: workspaceId,
    social_account_id: socialAccountId,
    metric_date: row.metricDate,
    followers: row.followers || 0,
    followers_gained: row.followersGained || 0,
    reach: row.reach || 0,
    impressions: row.impressions || 0,
    engagement: row.engagement || 0,
    video_views: row.videoViews || 0,
    watch_time_seconds: row.watchTimeSeconds || 0,
    comments: row.comments || 0,
    shares: row.shares || 0,
    saves: row.saves || 0,
    raw: row.raw || {},
  }));
  const { error } = await admin.from("daily_channel_metrics").upsert(payload, {
    onConflict: "social_account_id,metric_date",
  });
  if (error) throw error;
}

async function upsertContentSnapshots(
  admin: ReturnType<typeof createAdminClient>,
  workspaceId: string,
  socialAccountId: string,
  rows: Array<Record<string, unknown>>,
) {
  if (!rows.length) return;
  const payload = rows.map((row) => ({
    workspace_id: workspaceId,
    social_account_id: socialAccountId,
    platform_content_id: row.platformContentId,
    title: row.title || "",
    caption: row.caption || "",
    content_type: row.contentType || "post",
    thumbnail_url: row.thumbnailUrl || "",
    permalink: row.permalink || "",
    published_at: row.publishedAt || null,
    snapshot_date: new Date().toISOString().slice(0, 10),
    reach: row.reach || 0,
    engagement: row.engagement || 0,
    comments: row.comments || 0,
    shares: row.shares || 0,
    saves: row.saves || 0,
    followers_gained: row.followersGained || 0,
    performance_score: row.performanceScore || 0,
    video_views: row.videoViews || 0,
    watch_time_seconds: row.watchTimeSeconds || 0,
    raw: row.raw || {},
  }));
  const { error } = await admin.from("content_snapshots").upsert(payload, {
    onConflict: "social_account_id,platform_content_id",
  });
  if (error) throw error;
}

function computePerformanceScore(reach: number, engagement: number) {
  if (!reach) return 0;
  const rate = (engagement / Math.max(reach, 1)) * 100;
  return Math.max(0, Math.min(100, Math.round(rate * 10)));
}

async function syncYouTubeAccount(admin: ReturnType<typeof createAdminClient>, account: AccountRow, tokens: any) {
  const headers = { Authorization: `Bearer ${tokens.access_token}` };
  const channelResp = await fetchJson<any>(
    "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&mine=true",
    { headers },
  );
  const channel = channelResp.items?.[0];
  if (!channel) throw new Error("YouTube channel not found");

  const followers = Number(channel.statistics?.subscriberCount || 0);
  const avatarUrl =
    channel.snippet?.thumbnails?.medium?.url ||
    channel.snippet?.thumbnails?.default?.url ||
    "";
  const uploadsPlaylistId = channel.contentDetails?.relatedPlaylists?.uploads || "";

  await admin
    .from("social_accounts")
    .update({
      account_name: channel.snippet?.title || account.account_name,
      account_handle: channel.snippet?.customUrl || account.account_handle,
      avatar_url: avatarUrl,
      follower_count: followers,
      connection_status: "connected",
      last_error: "",
      last_health_check_at: new Date().toISOString(),
      metadata: {
        ...(account.metadata || {}),
        view_count: Number(channel.statistics?.viewCount || 0),
        video_count: Number(channel.statistics?.videoCount || 0),
        uploads_playlist_id: uploadsPlaylistId,
      },
    })
    .eq("id", account.id);

  let playlistItems: any[] = [];
  if (uploadsPlaylistId) {
    const playlistResp = await fetchJson<any>(
      `https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId=${encodeURIComponent(uploadsPlaylistId)}&maxResults=20`,
      { headers },
    );
    playlistItems = playlistResp.items || [];
  }
  const videoIds = playlistItems.map((item) => item.contentDetails?.videoId).filter(Boolean);
  let videoMap = new Map<string, any>();
  if (videoIds.length) {
    const videosResp = await fetchJson<any>(
      `https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id=${encodeURIComponent(videoIds.join(","))}`,
      { headers },
    );
    videoMap = new Map((videosResp.items || []).map((item: any) => [item.id, item]));
  }

  const contents = playlistItems.map((item) => {
    const videoId = item.contentDetails?.videoId;
    const video = videoMap.get(videoId) || {};
    const views = Number(video.statistics?.viewCount || 0);
    const comments = Number(video.statistics?.commentCount || 0);
    const likes = Number(video.statistics?.likeCount || 0);
    const shares = 0;
    const engagement = likes + comments + shares;
    const title = video.snippet?.title || item.snippet?.title || "YouTube content";
    const publishedAt = video.snippet?.publishedAt || item.contentDetails?.videoPublishedAt || item.snippet?.publishedAt || null;
    const thumbnailUrl =
      video.snippet?.thumbnails?.medium?.url ||
      video.snippet?.thumbnails?.default?.url ||
      "";
    return {
      platformContentId: String(videoId),
      title,
      caption: video.snippet?.description || "",
      contentType: title.includes("#Shorts") ? "short" : "video",
      thumbnailUrl,
      permalink: videoId ? `https://www.youtube.com/watch?v=${videoId}` : "",
      publishedAt,
      reach: views,
      engagement,
      comments,
      shares,
      saves: 0,
      followersGained: 0,
      performanceScore: computePerformanceScore(views, engagement),
      videoViews: views,
      watchTimeSeconds: 0,
      raw: video,
    };
  });

  await upsertContentSnapshots(admin, account.workspace_id, account.id, contents);

  const endDate = new Date().toISOString().slice(0, 10);
  const start = new Date();
  start.setDate(start.getDate() - 29);
  const startDate = start.toISOString().slice(0, 10);
  let metricRows: any[] = [];
  try {
    const analytics = await fetchJson<any>(
      `https://youtubeanalytics.googleapis.com/v2/reports?ids=channel==MINE&startDate=${startDate}&endDate=${endDate}&metrics=views,comments,likes,shares,subscribersGained,subscribersLost,estimatedMinutesWatched,averageViewDuration&dimensions=day&sort=day`,
      { headers },
    );
    metricRows = (analytics.rows || []).map((row: any) => ({
      metricDate: row[0],
      followers: followers,
      followersGained: Number(row[5] || 0) - Number(row[6] || 0),
      reach: Number(row[1] || 0),
      impressions: Number(row[1] || 0),
      engagement: Number(row[2] || 0) + Number(row[3] || 0) + Number(row[4] || 0),
      videoViews: Number(row[1] || 0),
      watchTimeSeconds: Math.round(Number(row[7] || 0) * 60),
      comments: Number(row[2] || 0),
      shares: Number(row[4] || 0),
      saves: 0,
      raw: { averageViewDuration: Number(row[8] || 0) },
    }));
  } catch {
    metricRows = [];
  }

  if (!metricRows.length) {
    const grouped = new Map<string, any>();
    for (const item of contents) {
      const date = String(item.publishedAt || "").slice(0, 10);
      if (!date) continue;
      const row = grouped.get(date) || {
        metricDate: date,
        followers,
        followersGained: 0,
        reach: 0,
        impressions: 0,
        engagement: 0,
        videoViews: 0,
        watchTimeSeconds: 0,
        comments: 0,
        shares: 0,
        saves: 0,
        raw: {},
      };
      row.reach += Number(item.reach || 0);
      row.impressions += Number(item.reach || 0);
      row.engagement += Number(item.engagement || 0);
      row.videoViews += Number(item.videoViews || 0);
      row.comments += Number(item.comments || 0);
      grouped.set(date, row);
    }
    metricRows = Array.from(grouped.values());
  }

  await upsertDailyMetrics(admin, account.workspace_id, account.id, metricRows);
}

async function syncTikTokAccount(admin: ReturnType<typeof createAdminClient>, account: AccountRow, tokens: any) {
  const headers = { Authorization: `Bearer ${tokens.access_token}` };
  const userInfo = await fetchJson<any>(
    "https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,avatar_url,display_name,follower_count,likes_count,video_count",
    { headers },
  );
  const user = userInfo.data?.user || {};
  const followers = Number(user.follower_count || 0);

  await admin
    .from("social_accounts")
    .update({
      account_name: user.display_name || account.account_name,
      avatar_url: user.avatar_url || account.avatar_url,
      follower_count: followers,
      connection_status: "connected",
      last_error: "",
      last_health_check_at: new Date().toISOString(),
      metadata: {
        ...(account.metadata || {}),
        union_id: user.union_id || "",
        likes_count: Number(user.likes_count || 0),
        video_count: Number(user.video_count || 0),
      },
    })
    .eq("id", account.id);

  const listed = await fetchJson<any>("https://open.tiktokapis.com/v2/video/list/", {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ max_count: 20 }),
  });
  const listedVideos = listed.data?.videos || [];
  const videoIds = listedVideos.map((item: any) => item.id).filter(Boolean);

  let videos: any[] = [];
  if (videoIds.length) {
    const queried = await fetchJson<any>(
      "https://open.tiktokapis.com/v2/video/query/?fields=id,create_time,title,cover_image_url,share_url,video_description,duration,like_count,comment_count,share_count,view_count",
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ filters: { video_ids: videoIds } }),
      },
    );
    videos = queried.data?.videos || [];
  }

  const contents = videos.map((video) => {
    const views = Number(video.view_count || 0);
    const comments = Number(video.comment_count || 0);
    const shares = Number(video.share_count || 0);
    const likes = Number(video.like_count || 0);
    const engagement = likes + comments + shares;
    return {
      platformContentId: String(video.id),
      title: video.title || video.video_description || "TikTok video",
      caption: video.video_description || "",
      contentType: "short",
      thumbnailUrl: video.cover_image_url || "",
      permalink: video.share_url || "",
      publishedAt: video.create_time ? new Date(Number(video.create_time) * 1000).toISOString() : null,
      reach: views,
      engagement,
      comments,
      shares,
      saves: 0,
      followersGained: 0,
      performanceScore: computePerformanceScore(views, engagement),
      videoViews: views,
      watchTimeSeconds: Number(video.duration || 0),
      raw: video,
    };
  });

  await upsertContentSnapshots(admin, account.workspace_id, account.id, contents);

  const grouped = new Map<string, any>();
  for (const item of contents) {
    const date = String(item.publishedAt || "").slice(0, 10);
    if (!date) continue;
    const row = grouped.get(date) || {
      metricDate: date,
      followers,
      followersGained: 0,
      reach: 0,
      impressions: 0,
      engagement: 0,
      videoViews: 0,
      watchTimeSeconds: 0,
      comments: 0,
      shares: 0,
      saves: 0,
      raw: {},
    };
    row.reach += Number(item.reach || 0);
    row.impressions += Number(item.reach || 0);
    row.engagement += Number(item.engagement || 0);
    row.videoViews += Number(item.videoViews || 0);
    row.watchTimeSeconds += Number(item.watchTimeSeconds || 0);
    row.comments += Number(item.comments || 0);
    row.shares += Number(item.shares || 0);
    grouped.set(date, row);
  }

  await upsertDailyMetrics(admin, account.workspace_id, account.id, Array.from(grouped.values()));
}

async function syncFacebookAccount(admin: ReturnType<typeof createAdminClient>, account: AccountRow, tokens: any) {
  const base = "https://graph.facebook.com/v20.0";
  const page = await fetchJson<any>(
    `${base}/${encodeURIComponent(account.account_platform_id)}?fields=id,name,fan_count,followers_count,picture{url}&access_token=${encodeURIComponent(tokens.access_token)}`,
  );
  const followers = Number(page.followers_count || page.fan_count || 0);

  await admin
    .from("social_accounts")
    .update({
      account_name: page.name || account.account_name,
      avatar_url: page.picture?.data?.url || account.avatar_url,
      follower_count: followers,
      connection_status: "connected",
      last_error: "",
      last_health_check_at: new Date().toISOString(),
    })
    .eq("id", account.id);

  const posts = await fetchJson<any>(
    `${base}/${encodeURIComponent(account.account_platform_id)}/posts?fields=id,message,created_time,full_picture,permalink_url,shares,reactions.summary(true),comments.summary(true)&limit=20&access_token=${encodeURIComponent(tokens.access_token)}`,
  );
  const rows = posts.data || [];
  const contents = rows.map((post: any) => {
    const comments = Number(post.comments?.summary?.total_count || 0);
    const shares = Number(post.shares?.count || 0);
    const reactions = Number(post.reactions?.summary?.total_count || 0);
    const reach = reactions * 12 + comments * 8 + shares * 20;
    const engagement = reactions + comments + shares;
    return {
      platformContentId: String(post.id),
      title: (post.message || "Facebook post").slice(0, 80),
      caption: post.message || "",
      contentType: "post",
      thumbnailUrl: post.full_picture || "",
      permalink: post.permalink_url || "",
      publishedAt: post.created_time || null,
      reach,
      engagement,
      comments,
      shares,
      saves: 0,
      followersGained: 0,
      performanceScore: computePerformanceScore(reach, engagement),
      videoViews: 0,
      watchTimeSeconds: 0,
      raw: post,
    };
  });

  await upsertContentSnapshots(admin, account.workspace_id, account.id, contents);

  let metrics: any[] = [];
  try {
    const insights = await fetchJson<any>(
      `${base}/${encodeURIComponent(account.account_platform_id)}/insights?metric=page_impressions,page_post_engagements,page_fans&period=day&access_token=${encodeURIComponent(tokens.access_token)}`,
    );
    const metricMap: Record<string, any> = {};
    for (const item of insights.data || []) {
      for (const value of item.values || []) {
        const date = String(value.end_time || "").slice(0, 10);
        if (!date) continue;
        metricMap[date] ||= {
          metricDate: date,
          followers,
          followersGained: 0,
          reach: 0,
          impressions: 0,
          engagement: 0,
          videoViews: 0,
          watchTimeSeconds: 0,
          comments: 0,
          shares: 0,
          saves: 0,
          raw: {},
        };
        if (item.name === "page_impressions") {
          metricMap[date].reach = Number(value.value || 0);
          metricMap[date].impressions = Number(value.value || 0);
        }
        if (item.name === "page_post_engagements") {
          metricMap[date].engagement = Number(value.value || 0);
        }
        if (item.name === "page_fans") {
          metricMap[date].followers = Number(value.value || 0);
        }
      }
    }
    metrics = Object.values(metricMap);
  } catch {
    metrics = [];
  }

  if (!metrics.length) {
    const grouped = new Map<string, any>();
    for (const item of contents) {
      const date = String(item.publishedAt || "").slice(0, 10);
      if (!date) continue;
      const row = grouped.get(date) || {
        metricDate: date,
        followers,
        followersGained: 0,
        reach: 0,
        impressions: 0,
        engagement: 0,
        videoViews: 0,
        watchTimeSeconds: 0,
        comments: 0,
        shares: 0,
        saves: 0,
        raw: {},
      };
      row.reach += Number(item.reach || 0);
      row.impressions += Number(item.reach || 0);
      row.engagement += Number(item.engagement || 0);
      row.comments += Number(item.comments || 0);
      row.shares += Number(item.shares || 0);
      grouped.set(date, row);
    }
    metrics = Array.from(grouped.values());
  }

  await upsertDailyMetrics(admin, account.workspace_id, account.id, metrics);
}

async function syncAccount(admin: ReturnType<typeof createAdminClient>, account: AccountRow) {
  const tokens = await ensureFreshTokens(admin, account, await getTokens(admin, account.id));
  if (account.platform === "youtube") {
    return syncYouTubeAccount(admin, account, tokens);
  }
  if (account.platform === "tiktok") {
    return syncTikTokAccount(admin, account, tokens);
  }
  if (account.platform === "facebook") {
    return syncFacebookAccount(admin, account, tokens);
  }
}

async function buildState(admin: ReturnType<typeof createAdminClient>, user: any, workspaceContext: WorkspaceContext) {
  const workspaceId = workspaceContext.workspace.id;
  const [{ data: groups }, { data: accounts }, { data: dailyMetrics }, { data: contents }, { data: inbox }, { data: settings }, { data: members }, { data: profile }] =
    await Promise.all([
      admin.from("channel_groups").select("*").eq("workspace_id", workspaceId).eq("is_archived", false).order("position"),
      admin.from("social_accounts").select("*").eq("workspace_id", workspaceId).order("platform").order("account_name"),
      admin
        .from("daily_channel_metrics")
        .select("*")
        .eq("workspace_id", workspaceId)
        .gte("metric_date", new Date(Date.now() - 29 * 86400000).toISOString().slice(0, 10))
        .order("metric_date"),
      admin.from("content_snapshots").select("*").eq("workspace_id", workspaceId).order("published_at", { ascending: false }).limit(200),
      admin.from("inbox_messages").select("*").eq("workspace_id", workspaceId).order("received_at", { ascending: false }).limit(50),
      admin.from("user_settings").select("*").eq("user_id", user.id).maybeSingle(),
      admin
        .from("workspace_members")
        .select("id, role, profile:profiles(full_name, email, avatar_url, username)")
        .eq("workspace_id", workspaceId),
      admin.from("profiles").select("*").eq("id", user.id).maybeSingle(),
    ]);

  const accountRows = (accounts || []) as AccountRow[];
  const accountIds = accountRows.map((item) => item.id);
  const { data: tokenRows } = accountIds.length
    ? await admin.from("social_account_tokens").select("*").in("social_account_id", accountIds)
    : { data: [] as any[] };
  const metricRows = (dailyMetrics || []) as any[];
  const contentRows = (contents || []) as any[];
  const inboxRows = (inbox || []) as any[];
  const groupRows = (groups || []) as any[];
  const tokensByAccount = new Map(((tokenRows || []) as any[]).map((item) => [item.social_account_id, item]));

  const groupMap = new Map(groupRows.map((item) => [item.id, item]));
  const metricsByAccount = new Map<string, any[]>();
  for (const metric of metricRows) {
    const key = metric.social_account_id;
    if (!metricsByAccount.has(key)) metricsByAccount.set(key, []);
    metricsByAccount.get(key)!.push(metric);
  }

  const contentsByAccount = new Map<string, any[]>();
  for (const content of contentRows) {
    const key = content.social_account_id;
    if (!contentsByAccount.has(key)) contentsByAccount.set(key, []);
    contentsByAccount.get(key)!.push(content);
  }

  const workspaceFollowers = accountRows.reduce((sum, item) => sum + Number(item.follower_count || 0), 0);

  const serializedGroups = [
    {
      id: "all",
      name: "Tất cả kênh (Workspace)",
      channelsCount: accountRows.length,
      followers: compactNumber(workspaceFollowers),
      health: accountRows.some((item) => item.connection_status === "error") ? "error" : accountRows.some((item) => item.connection_status === "warning") ? "warning" : "healthy",
      platforms: Array.from(new Set(accountRows.map((item) => item.platform))),
      isPinned: true,
    },
    ...groupRows.map((group) => {
      const groupAccounts = accountRows.filter((item) => item.channel_group_id === group.id);
      return {
        id: group.id,
        name: group.name,
        channelsCount: groupAccounts.length,
        followers: compactNumber(groupAccounts.reduce((sum, item) => sum + Number(item.follower_count || 0), 0)),
        health: groupAccounts.some((item) => item.connection_status === "error") ? "error" : groupAccounts.some((item) => item.connection_status === "warning") ? "warning" : "healthy",
        platforms: Array.from(new Set(groupAccounts.map((item) => item.platform))),
        growth: "+0%",
        isPinned: Boolean(group.is_favorite),
        description: group.description || "",
      };
    }),
  ];

  const serializedChannels = accountRows.map((item) => ({
    id: item.id,
    groupId: item.channel_group_id || "all",
    name: item.account_name,
    platform: item.platform,
    followers: compactNumber(item.follower_count),
    handle: item.account_handle || item.account_platform_id,
    status: item.connection_status === "connected" ? "connected" : "disconnected",
    lastSync: item.last_health_check_at ? new Date(item.last_health_check_at).toLocaleString("vi-VN") : "Chưa đồng bộ",
    avatar: item.avatar_url || `https://api.dicebear.com/7.x/identicon/svg?seed=${item.id}`,
    nativeId: item.account_platform_id,
    lastError: item.last_error || "",
  }));

  const serializedContents = contentRows.map((item: any, index: number) => {
    const account = accountRows.find((row) => row.id === item.social_account_id);
    return {
      id: item.id,
      thumbnail: item.thumbnail_url || `https://picsum.photos/seed/${item.id}/200/200`,
      title: item.title || "Nội dung chưa đặt tên",
      caption: item.caption || "",
      channel: account?.account_name || "Kênh",
      channelId: item.social_account_id,
      groupId: account?.channel_group_id || "all",
      platform: account?.platform || "facebook",
      date: item.published_at || new Date().toISOString(),
      reach: Number(item.reach || 0),
      engagement: Number(item.engagement || 0),
      comments: Number(item.comments || 0),
      shares: Number(item.shares || 0),
      saves: Number(item.saves || 0),
      followersGained: Number(item.followers_gained || 0),
      performanceScore: Number(item.performance_score || 0),
      score: Number(item.performance_score || 0),
      status: "published",
      type: item.content_type || "post",
      pillar: ["Giáo dục", "Sản phẩm", "Hậu trường", "Khách hàng", "Xu hướng"][index % 5],
      growthImpact: Number(item.performance_score || 0) >= 85 ? "+High" : "Medium",
      engagementRate: Number(item.reach || 0) > 0 ? Math.round((Number(item.engagement || 0) / Math.max(Number(item.reach || 0), 1)) * 1000) / 10 : 0,
      videoViews: Number(item.video_views || 0),
      watchTimeSeconds: Number(item.watch_time_seconds || 0),
    };
  });

  const serializedPosts = contentRows.map((item: any) => {
    const account = accountRows.find((row) => row.id === item.social_account_id);
    const effectiveDate = item.published_at ? new Date(item.published_at) : new Date();
    const today = new Date();
    const offset = Math.round((effectiveDate.getTime() - today.getTime()) / 86400000);
    return {
      id: item.id,
      postId: item.id,
      title: item.title || "Nội dung",
      time: effectiveDate.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }),
      date: effectiveDate.toISOString().slice(0, 10),
      dateOffset: offset,
      platform: account?.platform || "facebook",
      channel: account?.account_name || "Kênh",
      status: "published",
      type: item.content_type || "post",
      perfScore: Number(item.performance_score || 0),
      content: item.caption || "",
      caption: item.caption || "",
      accountId: item.social_account_id,
    };
  });

  const trendMap = new Map<string, any>();
  for (const metric of metricRows) {
    const date = metric.metric_date;
    if (!trendMap.has(date)) {
      trendMap.set(date, {
        date: new Date(`${date}T00:00:00Z`).toLocaleDateString("en-US", { month: "short", day: "2-digit", timeZone: "UTC" }),
        facebook: 0,
        youtube: 0,
        tiktok: 0,
        total: 0,
      });
    }
    const row = trendMap.get(date)!;
    const account = accountRows.find((item) => item.id === metric.social_account_id);
    if (account) {
      row[account.platform] += Number(metric.reach || 0);
    }
    row.total += Number(metric.reach || 0);
  }
  const trendData = Array.from(trendMap.values());

  const totals = metricRows.reduce(
    (acc, item) => {
      acc.reach += Number(item.reach || 0);
      acc.engagement += Number(item.engagement || 0);
      acc.followers += Number(item.followers_gained || 0);
      acc.views += Number(item.video_views || 0);
      return acc;
    },
    { reach: 0, engagement: 0, followers: 0, views: 0 },
  );

  const kpis = [
    { title: "Tổng Reach", value: compactNumber(totals.reach), change: "+0%", trend: "up", period: "30 ngày", platforms: ["facebook", "youtube", "tiktok"], trendData: [2, 4, 5, 7, 8, 10] },
    { title: "Tổng Tương Tác", value: compactNumber(totals.engagement), change: "+0%", trend: "up", period: "30 ngày", platforms: ["facebook", "youtube", "tiktok"], trendData: [3, 3, 5, 6, 8, 9] },
    { title: "Followers Mới", value: compactNumber(totals.followers), change: "+0%", trend: "up", period: "30 ngày", platforms: ["facebook", "youtube", "tiktok"], trendData: [1, 2, 2, 4, 5, 6] },
    { title: "Lượt Xem Video", value: compactNumber(totals.views), change: "+0%", trend: "up", period: "30 ngày", platforms: ["youtube", "tiktok"], trendData: [2, 5, 4, 8, 9, 11] },
    { title: "Nội Dung", value: compactNumber(contentRows.length), change: "read only", trend: "up", period: "toàn bộ", platforms: ["facebook", "youtube", "tiktok"], trendData: [1, 2, 3, 3, 4, 5] },
    { title: "Tần Suất Đồng Bộ", value: accountRows.length ? "100%" : "0%", change: "health check", trend: "up", period: "hệ thống", platforms: ["facebook", "youtube", "tiktok"], trendData: [4, 4, 5, 5, 6, 6] },
  ];

  const alerts = accountRows
    .filter((item) => item.connection_status !== "connected")
    .map((item) => ({
      id: `status-${item.id}`,
      title: `Kết nối ${item.platform} cần kiểm tra`,
      message: item.last_error || "Token hoặc phiên kết nối không còn ổn định.",
      type: "warning",
      severity: "warning",
      time: "hiện tại",
    }));

  const selectedAccount = accountRows[0] || null;
  const selectedMetrics = selectedAccount ? metricsByAccount.get(selectedAccount.id) || [] : [];
  const selectedContents = selectedAccount ? (contentsByAccount.get(selectedAccount.id) || []).slice(0, 8) : [];
  const selectedInbox = selectedAccount ? inboxRows.filter((item) => item.social_account_id === selectedAccount.id) : [];
  const heatMapDays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const heatCounter = new Map<string, number>();
  for (const message of selectedInbox) {
    const date = new Date(message.received_at);
    const day = date.toLocaleDateString("en-US", { weekday: "short" });
    const hour = date.getHours();
    heatCounter.set(`${day}:${hour}`, (heatCounter.get(`${day}:${hour}`) || 0) + 1);
  }
  const heatmapData = heatMapDays.map((day) => ({
    name: day,
    data: Array.from({ length: 24 }, (_, hour) => ({
      hour,
      value: heatCounter.get(`${day}:${hour}`) || 0,
    })),
  }));

  const channelAnalytics = selectedAccount
    ? {
        selected: serializedChannels.find((item) => item.id === selectedAccount.id) || null,
        summary: {
          groupName: groupMap.get(selectedAccount.channel_group_id || "")?.name || "Chưa phân nhóm",
          connectionLabel: selectedAccount.connection_status === "connected" ? "Kết nối ổn định" : "Cần kiểm tra kết nối",
          syncLabel: selectedAccount.last_health_check_at ? "Vừa xong" : "Chưa đồng bộ",
          handle: selectedAccount.account_handle || selectedAccount.account_platform_id,
          avgResponseMinutes: 0,
          latestReach: Number(selectedMetrics[selectedMetrics.length - 1]?.reach || 0),
          previousReach: Number(selectedMetrics[selectedMetrics.length - 2]?.reach || 0),
          latestEngagement: Number(selectedMetrics[selectedMetrics.length - 1]?.engagement || 0),
          videoViews: selectedMetrics.reduce((sum, row) => sum + Number(row.video_views || 0), 0),
        },
        kpis: [
          { label: "Followers", value: compactNumber(selectedAccount.follower_count), change: "+0%", trend: "up" },
          { label: "Video Views", value: compactNumber(selectedMetrics.reduce((sum, row) => sum + Number(row.video_views || 0), 0)), change: "+0%", trend: "up" },
          { label: "Watch Time", value: compactNumber(Math.round(selectedMetrics.reduce((sum, row) => sum + Number(row.watch_time_seconds || 0), 0) / 3600)), change: "+0%", trend: "up" },
          { label: "Avg Response", value: "0m", change: "read only", trend: "up" },
          { label: "Engagement", value: compactNumber(selectedMetrics.reduce((sum, row) => sum + Number(row.engagement || 0), 0)), change: "+0%", trend: "up" },
          { label: "Reach", value: compactNumber(selectedMetrics.reduce((sum, row) => sum + Number(row.reach || 0), 0)), change: "+0%", trend: "up" },
        ],
        trendData: selectedMetrics.map((row) => ({
          date: new Date(`${row.metric_date}T00:00:00Z`).toLocaleDateString("en-US", { month: "short", day: "2-digit", timeZone: "UTC" }),
          total: Number(row.reach || 0),
          [selectedAccount.platform]: Number(row.reach || 0),
        })),
        heatmapData,
        comments: selectedInbox.map((item) => ({
          id: item.id,
          channel: selectedAccount.account_name,
          channelId: selectedAccount.id,
          platform: item.platform,
          type: item.message_type === "dm" ? "inbox" : "comment",
          authorName: item.sender_name,
          authorAvatar: item.sender_avatar_url || `https://api.dicebear.com/7.x/identicon/svg?seed=${item.id}`,
          handle: item.sender_handle,
          content: item.body,
          body: item.body,
          timestamp: new Date(item.received_at).toLocaleString("vi-VN"),
          receivedAt: item.received_at,
          postTitle: "",
          isRead: item.status !== "unread",
          status: item.status,
          sentiment: item.sentiment,
          replies: [],
        })),
        channels: serializedChannels,
        topContent: serializedContents.filter((item) => item.channelId === selectedAccount.id).slice(0, 8),
      }
    : { channels: [], trendData: [], heatmapData: [], selected: null };

  const platformData = Object.entries(
    serializedChannels.reduce((acc: Record<string, number>, item) => {
      const parsed = Number(String(item.followers).replace(/[^\d.]/g, "")) || 0;
      acc[item.platform] = (acc[item.platform] || 0) + parsed;
      return acc;
    }, {}),
  ).map(([name, value]) => ({ name: name.charAt(0).toUpperCase() + name.slice(1), value }));

  return {
    workspace: workspaceContext.workspace,
    user: {
      name: profile?.full_name || user.user_metadata?.full_name || user.email,
      email: user.email,
      username: profile?.username || user.user_metadata?.username || user.email?.split("@")[0] || "",
      role: workspaceContext.membership.role.toUpperCase(),
      avatar: profile?.avatar_url || "",
    },
    groups: serializedGroups,
    channels: serializedChannels,
    posts: serializedPosts,
    contents: serializedContents,
    alerts,
    kpis,
    trendData,
    inbox: channelAnalytics.comments || [],
    settings: {
      notifications: {
        email: settings?.email_notifications ?? true,
        push: settings?.push_notifications ?? true,
        alerts: settings?.alert_notifications ?? true,
      },
    },
    systemUsers: (members || []).map((item: any) => ({
      id: item.id,
      name: item.profile?.full_name || item.profile?.email || "User",
      email: item.profile?.email || "",
      role: String(item.role || "viewer").toUpperCase(),
      status: "Dang hoat dong",
      avatar: item.profile?.avatar_url || `https://api.dicebear.com/7.x/identicon/svg?seed=${item.id}`,
    })),
    reports: {
      kpis: [
        { title: "Tong Reach", value: compactNumber(totals.reach), delta: 0, sparklineData: trendData.map((item: any) => item.total) },
        { title: "Ti le Tuong Tac", value: `${Math.round((totals.engagement / Math.max(totals.reach, 1)) * 1000) / 10}%`, delta: 0, sparklineData: trendData.map((item: any) => item.total) },
        { title: "Follower Moi", value: compactNumber(totals.followers), delta: 0, sparklineData: trendData.map((item: any) => item.total) },
        { title: "Video Views", value: compactNumber(totals.views), delta: 0, sparklineData: trendData.map((item: any) => item.total) },
      ],
      viewsData: trendData.map((item: any) => ({ name: item.date, views: item.total, engagement: item.total })),
      platformData,
      compact: [
        { title: "Tin Nhan Moi", value: compactNumber(inboxRows.length), delta: 0 },
        { title: "Binh Luan", value: compactNumber(serializedContents.reduce((sum, item) => sum + Number(item.comments || 0), 0)), delta: 0 },
        { title: "Chia Se", value: compactNumber(serializedContents.reduce((sum, item) => sum + Number(item.shares || 0), 0)), delta: 0 },
        { title: "Luu Bai", value: compactNumber(serializedContents.reduce((sum, item) => sum + Number(item.saves || 0), 0)), delta: 0 },
      ],
    },
    channelAnalytics,
    urls: {
      connectChannel: `${env.appUrl}/api/oauth/start`,
      logout: `${env.appUrl}/login`,
    },
  };
}

async function buildStateV2(admin: ReturnType<typeof createAdminClient>, user: any, workspaceContext: WorkspaceContext) {
  const workspaceId = workspaceContext.workspace.id;
  const [{ data: groups }, { data: accounts }, { data: dailyMetrics }, { data: contents }, { data: inbox }, { data: settings }, { data: members }, { data: profile }] =
    await Promise.all([
      admin.from("channel_groups").select("*").eq("workspace_id", workspaceId).eq("is_archived", false).order("position"),
      admin.from("social_accounts").select("*").eq("workspace_id", workspaceId).order("platform").order("account_name"),
      admin
        .from("daily_channel_metrics")
        .select("*")
        .eq("workspace_id", workspaceId)
        .gte("metric_date", new Date(Date.now() - 29 * 86400000).toISOString().slice(0, 10))
        .order("metric_date"),
      admin.from("content_snapshots").select("*").eq("workspace_id", workspaceId).order("published_at", { ascending: false }).limit(200),
      admin.from("inbox_messages").select("*").eq("workspace_id", workspaceId).order("received_at", { ascending: false }).limit(50),
      admin.from("user_settings").select("*").eq("user_id", user.id).maybeSingle(),
      admin.from("workspace_members").select("id, user_id, role, profile:profiles(full_name, email, avatar_url, username)").eq("workspace_id", workspaceId),
      admin.from("profiles").select("*").eq("id", user.id).maybeSingle(),
    ]);

  const accountRows = (accounts || []) as AccountRow[];
  const accountIds = accountRows.map((item) => item.id);
  const { data: tokenRows } = accountIds.length ? await admin.from("social_account_tokens").select("*").in("social_account_id", accountIds) : { data: [] as any[] };
  const metricRows = (dailyMetrics || []) as any[];
  const contentRows = (contents || []) as any[];
  const inboxRows = (inbox || []) as any[];
  const groupRows = (groups || []) as any[];
  const memberRows = (members || []) as any[];

  const tokensByAccount = new Map(((tokenRows || []) as any[]).map((item) => [item.social_account_id, item]));
  const groupMap = new Map(groupRows.map((item) => [item.id, item]));
  const memberByUserId = new Map(memberRows.map((item) => [item.user_id, item]));
  const metricsByAccount = new Map<string, any[]>();

  for (const metric of metricRows) {
    const key = metric.social_account_id;
    if (!metricsByAccount.has(key)) metricsByAccount.set(key, []);
    metricsByAccount.get(key)!.push(metric);
  }

  const workspaceFollowers = accountRows.reduce((sum, item) => sum + Number(item.follower_count || 0), 0);

  const serializedGroups = [
    {
      id: "all",
      name: "Tất cả kênh (Workspace)",
      channelsCount: accountRows.length,
      followers: compactNumber(workspaceFollowers),
      health: accountRows.some((item) => item.connection_status === "error") ? "error" : accountRows.some((item) => item.connection_status === "warning") ? "warning" : "healthy",
      platforms: Array.from(new Set(accountRows.map((item) => item.platform))),
      isPinned: true,
    },
    ...groupRows.map((group) => {
      const groupAccounts = accountRows.filter((item) => item.channel_group_id === group.id);
      return {
        id: group.id,
        name: group.name,
        channelsCount: groupAccounts.length,
        followers: compactNumber(groupAccounts.reduce((sum, item) => sum + Number(item.follower_count || 0), 0)),
        health: groupAccounts.some((item) => item.connection_status === "error") ? "error" : groupAccounts.some((item) => item.connection_status === "warning") ? "warning" : "healthy",
        platforms: Array.from(new Set(groupAccounts.map((item) => item.platform))),
        growth: "+0%",
        isPinned: Boolean(group.is_favorite),
        description: group.description || "",
      };
    }),
  ];

  const serializedChannels = accountRows.map((item) => {
    const token = tokensByAccount.get(item.id);
    const metadata = (item.metadata || {}) as Record<string, any>;
    const tokenHealth = describeTokenHealth(item, token);
    const requiredScopes = requiredScopesForPlatform(item.platform);
    const grantedScopes = parseGrantedScopes(token?.scope);
    const missingScopes = requiredScopes.filter((scope) => !grantedScopes.includes(scope));
    const connector = memberByUserId.get(item.connected_by);
    return {
      id: item.id,
      groupId: item.channel_group_id || "all",
      name: item.account_name,
      platform: item.platform,
      followers: compactNumber(item.follower_count),
      handle: item.account_handle || item.account_platform_id,
      status: item.connection_status === "connected" ? "connected" : "disconnected",
      connectionStatus: item.connection_status,
      reconnectRequired: tokenHealth.reconnectRequired,
      lastSync: item.last_health_check_at ? new Date(item.last_health_check_at).toLocaleString("vi-VN") : "Chưa đồng bộ",
      avatar: item.avatar_url || `https://api.dicebear.com/7.x/identicon/svg?seed=${item.id}`,
      nativeId: item.account_platform_id,
      lastError: item.last_error || "",
      tokenHealth,
      tokenExpiresAt: token?.token_expires_at || null,
      hasRefreshToken: Boolean(token?.refresh_token),
      tokenScope: token?.scope || "",
      grantedScopes,
      requiredScopes,
      missingScopes,
      connectionMethod: String(metadata.connection_method || token?.token_metadata?.import_mode || "oauth"),
      authAccountLabel: String(metadata.auth_account_label || item.account_name || ""),
      authAccountId: String(metadata.auth_account_id || ""),
      connectedByName: connector?.profile?.full_name || connector?.profile?.email || "",
      groupName: groupMap.get(item.channel_group_id || "")?.name || "Chưa phân nhóm",
      rawMetadata: metadata,
    };
  });

  const serializedContents = contentRows.map((item: any, index: number) => {
    const account = accountRows.find((row) => row.id === item.social_account_id);
    return {
      id: item.id,
      thumbnail: item.thumbnail_url || `https://picsum.photos/seed/${item.id}/200/200`,
      title: item.title || "Nội dung chưa đặt tên",
      caption: item.caption || "",
      channel: account?.account_name || "Kênh",
      channelId: item.social_account_id,
      groupId: account?.channel_group_id || "all",
      platform: account?.platform || "facebook",
      date: item.published_at || new Date().toISOString(),
      reach: Number(item.reach || 0),
      engagement: Number(item.engagement || 0),
      comments: Number(item.comments || 0),
      shares: Number(item.shares || 0),
      saves: Number(item.saves || 0),
      followersGained: Number(item.followers_gained || 0),
      performanceScore: Number(item.performance_score || 0),
      score: Number(item.performance_score || 0),
      status: "published",
      type: item.content_type || "post",
      pillar: ["Giáo dục", "Sản phẩm", "Hậu trường", "Khách hàng", "Xu hướng"][index % 5],
      growthImpact: Number(item.performance_score || 0) >= 85 ? "+High" : "Medium",
      engagementRate: Number(item.reach || 0) > 0 ? Math.round((Number(item.engagement || 0) / Math.max(Number(item.reach || 0), 1)) * 1000) / 10 : 0,
      videoViews: Number(item.video_views || 0),
      watchTimeSeconds: Number(item.watch_time_seconds || 0),
    };
  });

  const serializedPosts = contentRows.map((item: any) => {
    const account = accountRows.find((row) => row.id === item.social_account_id);
    const effectiveDate = item.published_at ? new Date(item.published_at) : new Date();
    const today = new Date();
    return {
      id: item.id,
      postId: item.id,
      title: item.title || "Nội dung",
      time: effectiveDate.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }),
      date: effectiveDate.toISOString().slice(0, 10),
      dateOffset: Math.round((effectiveDate.getTime() - today.getTime()) / 86400000),
      platform: account?.platform || "facebook",
      channel: account?.account_name || "Kênh",
      status: "published",
      type: item.content_type || "post",
      perfScore: Number(item.performance_score || 0),
      content: item.caption || "",
      caption: item.caption || "",
      accountId: item.social_account_id,
    };
  });

  const trendMap = new Map<string, any>();
  for (const metric of metricRows) {
    const date = metric.metric_date;
    if (!trendMap.has(date)) {
      trendMap.set(date, {
        date: new Date(`${date}T00:00:00Z`).toLocaleDateString("en-US", { month: "short", day: "2-digit", timeZone: "UTC" }),
        facebook: 0,
        youtube: 0,
        tiktok: 0,
        total: 0,
      });
    }
    const row = trendMap.get(date)!;
    const account = accountRows.find((item) => item.id === metric.social_account_id);
    if (account) row[account.platform] += Number(metric.reach || 0);
    row.total += Number(metric.reach || 0);
  }
  const trendData = Array.from(trendMap.values());

  const totals = metricRows.reduce(
    (acc, item) => {
      acc.reach += Number(item.reach || 0);
      acc.engagement += Number(item.engagement || 0);
      acc.followers += Number(item.followers_gained || 0);
      acc.views += Number(item.video_views || 0);
      return acc;
    },
    { reach: 0, engagement: 0, followers: 0, views: 0 },
  );

  const kpis = [
    { title: "Tổng Reach", value: compactNumber(totals.reach), change: "+0%", trend: "up", period: "30 ngày", platforms: ["facebook", "youtube", "tiktok"], trendData: [2, 4, 5, 7, 8, 10] },
    { title: "Tổng Tương Tác", value: compactNumber(totals.engagement), change: "+0%", trend: "up", period: "30 ngày", platforms: ["facebook", "youtube", "tiktok"], trendData: [3, 3, 5, 6, 8, 9] },
    { title: "Followers Mới", value: compactNumber(totals.followers), change: "+0%", trend: "up", period: "30 ngày", platforms: ["facebook", "youtube", "tiktok"], trendData: [1, 2, 2, 4, 5, 6] },
    { title: "Lượt Xem Video", value: compactNumber(totals.views), change: "+0%", trend: "up", period: "30 ngày", platforms: ["youtube", "tiktok"], trendData: [2, 5, 4, 8, 9, 11] },
    { title: "Nội Dung", value: compactNumber(contentRows.length), change: "read only", trend: "up", period: "toàn bộ", platforms: ["facebook", "youtube", "tiktok"], trendData: [1, 2, 3, 3, 4, 5] },
    { title: "Tần Suất Đồng Bộ", value: accountRows.length ? "100%" : "0%", change: "health check", trend: "up", period: "hệ thống", platforms: ["facebook", "youtube", "tiktok"], trendData: [4, 4, 5, 5, 6, 6] },
  ];

  const alerts = serializedChannels
    .filter(
      (item) =>
        item.connectionStatus !== "connected" ||
        item.missingScopes.length > 0 ||
        ["expiring", "expiring_refreshable", "expired", "expired_refreshable", "reconnect_required", "missing"].includes(item.tokenHealth.status),
    )
    .map((item) => ({
      id: `status-${item.id}`,
      title:
        item.missingScopes.length > 0
          ? `Scope ${item.platform} của ${item.name} đang thiếu`
          : item.connectionStatus !== "connected"
            ? `Kết nối ${item.platform} cần kiểm tra`
            : `Token ${item.platform} của ${item.name} cần chú ý`,
      message:
        item.missingScopes.length > 0
          ? `Thiếu ${item.missingScopes.length} quyền: ${item.missingScopes.join(", ")}`
          : item.lastError || item.tokenHealth.description || "Token hoặc phiên kết nối không còn ổn định.",
      type: item.tokenHealth.severity === "error" ? "warning" : "info",
      severity: item.tokenHealth.severity === "error" ? "warning" : item.tokenHealth.severity,
      time: "hiện tại",
    }));

  const selectedAccount = accountRows[0] || null;
  const selectedMetrics = selectedAccount ? metricsByAccount.get(selectedAccount.id) || [] : [];
  const selectedInbox = selectedAccount ? inboxRows.filter((item) => item.social_account_id === selectedAccount.id) : [];
  const heatMapDays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const heatCounter = new Map<string, number>();
  for (const message of selectedInbox) {
    const date = new Date(message.received_at);
    const day = date.toLocaleDateString("en-US", { weekday: "short" });
    const hour = date.getHours();
    heatCounter.set(`${day}:${hour}`, (heatCounter.get(`${day}:${hour}`) || 0) + 1);
  }
  const heatmapData = heatMapDays.map((day) => ({
    name: day,
    data: Array.from({ length: 24 }, (_, hour) => ({
      hour,
      value: heatCounter.get(`${day}:${hour}`) || 0,
    })),
  }));

  const selectedSerializedChannel = selectedAccount ? serializedChannels.find((item) => item.id === selectedAccount.id) || null : null;
  const channelAnalytics = selectedAccount
    ? {
        selected: selectedSerializedChannel,
        summary: {
          groupName: groupMap.get(selectedAccount.channel_group_id || "")?.name || "Chưa phân nhóm",
          connectionLabel: selectedSerializedChannel?.reconnectRequired ? "Cần kết nối lại" : "Kết nối ổn định",
          syncLabel: selectedAccount.last_health_check_at ? "Vừa xong" : "Chưa đồng bộ",
          handle: selectedAccount.account_handle || selectedAccount.account_platform_id,
          avgResponseMinutes: 0,
          latestReach: Number(selectedMetrics[selectedMetrics.length - 1]?.reach || 0),
          previousReach: Number(selectedMetrics[selectedMetrics.length - 2]?.reach || 0),
          latestEngagement: Number(selectedMetrics[selectedMetrics.length - 1]?.engagement || 0),
          videoViews: selectedMetrics.reduce((sum, row) => sum + Number(row.video_views || 0), 0),
        },
        kpis: [
          { label: "Followers", value: compactNumber(selectedAccount.follower_count), change: "+0%", trend: "up" },
          { label: "Video Views", value: compactNumber(selectedMetrics.reduce((sum, row) => sum + Number(row.video_views || 0), 0)), change: "+0%", trend: "up" },
          { label: "Watch Time", value: compactNumber(Math.round(selectedMetrics.reduce((sum, row) => sum + Number(row.watch_time_seconds || 0), 0) / 3600)), change: "+0%", trend: "up" },
          { label: "Avg Response", value: "0m", change: "read only", trend: "up" },
          { label: "Engagement", value: compactNumber(selectedMetrics.reduce((sum, row) => sum + Number(row.engagement || 0), 0)), change: "+0%", trend: "up" },
          { label: "Reach", value: compactNumber(selectedMetrics.reduce((sum, row) => sum + Number(row.reach || 0), 0)), change: "+0%", trend: "up" },
        ],
        trendData: selectedMetrics.map((row) => ({
          date: new Date(`${row.metric_date}T00:00:00Z`).toLocaleDateString("en-US", { month: "short", day: "2-digit", timeZone: "UTC" }),
          total: Number(row.reach || 0),
          [selectedAccount.platform]: Number(row.reach || 0),
        })),
        heatmapData,
        comments: selectedInbox.map((item) => ({
          id: item.id,
          channel: selectedAccount.account_name,
          channelId: selectedAccount.id,
          platform: item.platform,
          type: item.message_type === "dm" ? "inbox" : "comment",
          authorName: item.sender_name,
          authorAvatar: item.sender_avatar_url || `https://api.dicebear.com/7.x/identicon/svg?seed=${item.id}`,
          handle: item.sender_handle,
          content: item.body,
          body: item.body,
          timestamp: new Date(item.received_at).toLocaleString("vi-VN"),
          receivedAt: item.received_at,
          postTitle: "",
          isRead: item.status !== "unread",
          status: item.status,
          sentiment: item.sentiment,
          replies: [],
        })),
        channels: serializedChannels,
        topContent: serializedContents.filter((item) => item.channelId === selectedAccount.id).slice(0, 8),
      }
    : { channels: [], trendData: [], heatmapData: [], selected: null };

  const platformData = Object.entries(
    serializedChannels.reduce((acc: Record<string, number>, item) => {
      const parsed = Number(String(item.followers).replace(/[^\d.]/g, "")) || 0;
      acc[item.platform] = (acc[item.platform] || 0) + parsed;
      return acc;
    }, {}),
  ).map(([name, value]) => ({ name: name.charAt(0).toUpperCase() + name.slice(1), value }));

  return {
    workspace: workspaceContext.workspace,
    user: {
      name: profile?.full_name || user.user_metadata?.full_name || user.email,
      email: user.email,
      username: profile?.username || user.user_metadata?.username || user.email?.split("@")[0] || "",
      role: workspaceContext.membership.role.toUpperCase(),
      avatar: profile?.avatar_url || "",
    },
    groups: serializedGroups,
    channels: serializedChannels,
    posts: serializedPosts,
    contents: serializedContents,
    alerts,
    kpis,
    trendData,
    inbox: channelAnalytics.comments || [],
    settings: {
      notifications: {
        email: settings?.email_notifications ?? true,
        push: settings?.push_notifications ?? true,
        alerts: settings?.alert_notifications ?? true,
      },
    },
    systemUsers: memberRows.map((item: any) => ({
      id: item.id,
      name: item.profile?.full_name || item.profile?.email || "User",
      email: item.profile?.email || "",
      role: String(item.role || "viewer").toUpperCase(),
      status: "Dang hoat dong",
      avatar: item.profile?.avatar_url || `https://api.dicebear.com/7.x/identicon/svg?seed=${item.id}`,
    })),
    reports: {
      kpis: [
        { title: "Tong Reach", value: compactNumber(totals.reach), delta: 0, sparklineData: trendData.map((item: any) => item.total) },
        { title: "Ti le Tuong Tac", value: `${Math.round((totals.engagement / Math.max(totals.reach, 1)) * 1000) / 10}%`, delta: 0, sparklineData: trendData.map((item: any) => item.total) },
        { title: "Follower Moi", value: compactNumber(totals.followers), delta: 0, sparklineData: trendData.map((item: any) => item.total) },
        { title: "Video Views", value: compactNumber(totals.views), delta: 0, sparklineData: trendData.map((item: any) => item.total) },
      ],
      viewsData: trendData.map((item: any) => ({ name: item.date, views: item.total, engagement: item.total })),
      platformData,
      compact: [
        { title: "Tin Nhan Moi", value: compactNumber(inboxRows.length), delta: 0 },
        { title: "Binh Luan", value: compactNumber(serializedContents.reduce((sum, item) => sum + Number(item.comments || 0), 0)), delta: 0 },
        { title: "Chia Se", value: compactNumber(serializedContents.reduce((sum, item) => sum + Number(item.shares || 0), 0)), delta: 0 },
        { title: "Luu Bai", value: compactNumber(serializedContents.reduce((sum, item) => sum + Number(item.saves || 0), 0)), delta: 0 },
      ],
    },
    channelAnalytics,
    urls: {
      connectChannel: `${env.appUrl}/api/oauth/start`,
      logout: `${env.appUrl}/login`,
    },
  };
}

function facebookScopes() {
  return [
    "pages_show_list",
    "pages_read_engagement",
    "pages_read_user_content",
    "read_insights",
    "pages_manage_engagement",
  ];
}

function youtubeScopes() {
  return [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
  ];
}

function tiktokScopes() {
  return ["user.info.basic", "user.info.profile", "user.info.stats", "video.list"];
}

async function handleOAuthStart(event: Event, admin: ReturnType<typeof createAdminClient>, user: any) {
  const platform = queryValue(event, "platform") as "facebook" | "youtube" | "tiktok";
  const groupId = queryValue(event, "groupId");
  if (!["facebook", "youtube", "tiktok"].includes(platform)) {
    return response(400, { error: "Unsupported platform" });
  }
  const workspace = await ensureWorkspaceForUser(admin, user);
  const state = signedState({
    userId: user.id,
    workspaceId: workspace.workspace.id,
    platform,
    groupId,
    ts: String(Date.now()),
  });
  return oauthRedirect(buildOAuthAuthorizeUrl(platform, state));
}

async function handleOAuthCallback(event: Event, admin: ReturnType<typeof createAdminClient>) {
  const platform = getPath(event).split("/").filter(Boolean)[2] as "facebook" | "youtube" | "tiktok";
  const code = queryValue(event, "code");
  const stateValue = queryValue(event, "state");
  const error = queryValue(event, "error");
  if (error) {
    return redirect(`${env.appUrl}/manage?oauth_error=${encodeURIComponent(error)}`);
  }
  if (!code || !stateValue) {
    return redirect(`${env.appUrl}/manage?oauth_error=missing_code`);
  }

  let state: Record<string, string>;
  try {
    state = verifyState(stateValue);
  } catch (stateError: any) {
    return redirect(`${env.appUrl}/manage?oauth_error=${encodeURIComponent(stateError.message || "invalid_state")}`);
  }

  const membership = await getWorkspaceMembership(admin, state.workspaceId, state.userId);
  if (!membership) {
    return redirect(`${env.appUrl}/manage?oauth_error=workspace_access_lost`);
  }

  const redirectUri = `${env.appUrl}/api/oauth/callback/${platform}`;

  if (platform === "youtube") {
    const tokenBody = new URLSearchParams({
      code,
      client_id: env.googleClientId,
      client_secret: env.googleClientSecret,
      redirect_uri: redirectUri,
      grant_type: "authorization_code",
    });
    const token = await fetchJson<any>("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: tokenBody.toString(),
    });
    const profile = await fetchJson<any>(
      "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&mine=true",
      { headers: { Authorization: `Bearer ${token.access_token}` } },
    );
    const channel = profile.items?.[0];
    if (!channel) {
      return redirect(`${env.appUrl}/manage?oauth_error=no_channel`);
    }
    const account = await upsertAccount(admin, {
      workspaceId: state.workspaceId,
      channelGroupId: state.groupId || null,
      connectedBy: state.userId,
      platform,
      platformId: channel.id,
      name: channel.snippet?.title || "YouTube",
      handle: channel.snippet?.customUrl || "",
      avatarUrl: channel.snippet?.thumbnails?.medium?.url || "",
      followers: Number(channel.statistics?.subscriberCount || 0),
      metadata: {
        uploads_playlist_id: channel.contentDetails?.relatedPlaylists?.uploads || "",
        connection_method: "oauth",
        auth_account_label: channel.snippet?.title || "YouTube",
        auth_account_id: channel.id,
      },
    });
    await saveTokens(admin, account.id, {
      accessToken: token.access_token,
      refreshToken: token.refresh_token,
      expiresIn: token.expires_in,
      scope: token.scope,
      metadata: token,
    });
    await syncYouTubeAccount(admin, account, { access_token: token.access_token });
    return redirect(`${env.appUrl}/manage?connected=youtube`);
  }

  if (platform === "tiktok") {
    const tokenBody = new URLSearchParams({
      client_key: env.tiktokClientKey,
      client_secret: env.tiktokClientSecret,
      code,
      grant_type: "authorization_code",
      redirect_uri: redirectUri,
    });
    const token = await fetchJson<any>("https://open.tiktokapis.com/v2/oauth/token/", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: tokenBody.toString(),
    });
    const userInfo = await fetchJson<any>(
      "https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,avatar_url,display_name,follower_count",
      { headers: { Authorization: `Bearer ${token.access_token}` } },
    );
    const user = userInfo.data?.user || {};
    const account = await upsertAccount(admin, {
      workspaceId: state.workspaceId,
      channelGroupId: state.groupId || null,
      connectedBy: state.userId,
      platform,
      platformId: user.open_id,
      name: user.display_name || "TikTok",
      avatarUrl: user.avatar_url || "",
      followers: Number(user.follower_count || 0),
      metadata: {
        union_id: user.union_id || "",
        connection_method: "oauth",
        auth_account_label: user.display_name || "TikTok",
        auth_account_id: user.open_id || "",
      },
    });
    await saveTokens(admin, account.id, {
      accessToken: token.access_token,
      refreshToken: token.refresh_token,
      expiresIn: token.expires_in,
      scope: token.scope,
      metadata: token,
    });
    await syncTikTokAccount(admin, account, { access_token: token.access_token });
    return redirect(`${env.appUrl}/manage?connected=tiktok`);
  }

  const shortToken = await fetchJson<any>(
    `https://graph.facebook.com/v20.0/oauth/access_token?client_id=${encodeURIComponent(env.facebookAppId)}&client_secret=${encodeURIComponent(env.facebookAppSecret)}&redirect_uri=${encodeURIComponent(redirectUri)}&code=${encodeURIComponent(code)}`,
  );
  const token = await fetchJson<any>(
    `https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id=${encodeURIComponent(env.facebookAppId)}&client_secret=${encodeURIComponent(env.facebookAppSecret)}&fb_exchange_token=${encodeURIComponent(shortToken.access_token)}`,
  ).catch(() => shortToken);

  const authProfile = await fetchJson<any>(
    `https://graph.facebook.com/v20.0/me?fields=id,name&access_token=${encodeURIComponent(token.access_token)}`,
  ).catch(() => ({ id: "", name: "" }));

  const pages = await fetchJson<any>(
    `https://graph.facebook.com/v20.0/me/accounts?fields=id,name,access_token,picture{url},followers_count,fan_count&access_token=${encodeURIComponent(token.access_token)}`,
  );
  const pageRows = pages.data || [];
  for (const page of pageRows) {
    const account = await upsertAccount(admin, {
      workspaceId: state.workspaceId,
      channelGroupId: state.groupId || null,
      connectedBy: state.userId,
      platform,
      platformId: page.id,
      name: page.name || "Facebook Page",
      avatarUrl: page.picture?.data?.url || "",
      followers: Number(page.followers_count || page.fan_count || 0),
      metadata: {
        connection_method: "oauth",
        auth_account_label: authProfile.name || page.name || "Facebook",
        auth_account_id: authProfile.id || "",
      },
    });
    await saveTokens(admin, account.id, {
      accessToken: page.access_token,
      metadata: { source_token: token.access_token },
    });
    await syncFacebookAccount(admin, account, { access_token: page.access_token });
  }
  return redirect(`${env.appUrl}/manage?connected=facebook`);
}

async function handleTokenImport(event: Event, admin: ReturnType<typeof createAdminClient>, user: any) {
  const workspace = await ensureWorkspaceForUser(admin, user);
  const body = parseBody(event);
  const platform = String(body.platform || "") as "facebook" | "youtube" | "tiktok";
  const accessToken = String(body.accessToken || "").trim();
  const refreshToken = String(body.refreshToken || "").trim();
  const externalId = String(body.externalId || "").trim();
  const scope = String(body.scope || "").trim();
  const expiresIn = Number(body.expiresIn || 0);
  const groupId = body.groupId && body.groupId !== "all" ? String(body.groupId) : null;

  if (!["facebook", "youtube", "tiktok"].includes(platform)) {
    return response(400, { error: "Unsupported platform" });
  }

  if (!accessToken) {
    return response(400, { error: "Access token is required" });
  }

  if (platform === "facebook") {
    if (!externalId) {
      return response(400, { error: "Facebook Page ID is required for manual token import" });
    }
    const page = await fetchJson<any>(
      `https://graph.facebook.com/v20.0/${encodeURIComponent(externalId)}?fields=id,name,fan_count,followers_count,picture{url}&access_token=${encodeURIComponent(accessToken)}`,
    );
    const account = await upsertAccount(admin, {
      workspaceId: workspace.workspace.id,
      channelGroupId: groupId,
      connectedBy: user.id,
      platform: "facebook",
      platformId: String(page.id || externalId),
      name: page.name || "Facebook Page",
      avatarUrl: page.picture?.data?.url || "",
      followers: Number(page.followers_count || page.fan_count || 0),
      metadata: {
        import_mode: "manual_token",
        connection_method: "manual_token",
        auth_account_label: page.name || "Facebook Page",
        auth_account_id: String(page.id || externalId),
      },
    });
    await saveTokens(admin, account.id, {
      accessToken,
      scope,
      metadata: { import_mode: "manual_token" },
    });
    await syncFacebookAccount(admin, account, { access_token: accessToken });
    return response(200, { ok: true, platform: "facebook", accountId: account.id });
  }

  if (platform === "youtube") {
    const channelResp = await fetchJson<any>(
      "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&mine=true",
      { headers: { Authorization: `Bearer ${accessToken}` } },
    );
    const channel = channelResp.items?.[0];
    if (!channel) {
      return response(400, { error: "YouTube token is valid but no channel was found for the current account" });
    }
    const account = await upsertAccount(admin, {
      workspaceId: workspace.workspace.id,
      channelGroupId: groupId,
      connectedBy: user.id,
      platform: "youtube",
      platformId: String(channel.id),
      name: channel.snippet?.title || "YouTube Channel",
      handle: channel.snippet?.customUrl || "",
      avatarUrl: channel.snippet?.thumbnails?.medium?.url || channel.snippet?.thumbnails?.default?.url || "",
      followers: Number(channel.statistics?.subscriberCount || 0),
      metadata: {
        import_mode: "manual_token",
        uploads_playlist_id: channel.contentDetails?.relatedPlaylists?.uploads || "",
        connection_method: "manual_token",
        auth_account_label: channel.snippet?.title || "YouTube Channel",
        auth_account_id: String(channel.id),
      },
    });
    await saveTokens(admin, account.id, {
      accessToken,
      refreshToken: refreshToken || undefined,
      expiresIn: Number.isFinite(expiresIn) && expiresIn > 0 ? expiresIn : undefined,
      scope,
      metadata: { import_mode: "manual_token" },
    });
    await syncYouTubeAccount(admin, account, { access_token: accessToken, refresh_token: refreshToken || undefined });
    return response(200, { ok: true, platform: "youtube", accountId: account.id });
  }

  const userInfo = await fetchJson<any>(
    "https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,avatar_url,display_name,follower_count,likes_count,video_count",
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  const tiktokUser = userInfo.data?.user || {};
  if (!tiktokUser.open_id) {
    return response(400, { error: "TikTok token is valid but no user profile was returned" });
  }
  const account = await upsertAccount(admin, {
    workspaceId: workspace.workspace.id,
    channelGroupId: groupId,
    connectedBy: user.id,
    platform: "tiktok",
    platformId: String(tiktokUser.open_id),
    name: tiktokUser.display_name || "TikTok",
    avatarUrl: tiktokUser.avatar_url || "",
    followers: Number(tiktokUser.follower_count || 0),
    metadata: {
      import_mode: "manual_token",
      union_id: tiktokUser.union_id || "",
      likes_count: Number(tiktokUser.likes_count || 0),
      video_count: Number(tiktokUser.video_count || 0),
      connection_method: "manual_token",
      auth_account_label: tiktokUser.display_name || "TikTok",
      auth_account_id: String(tiktokUser.open_id),
    },
  });
  await saveTokens(admin, account.id, {
    accessToken,
    refreshToken: refreshToken || undefined,
    expiresIn: Number.isFinite(expiresIn) && expiresIn > 0 ? expiresIn : undefined,
    scope,
    metadata: { import_mode: "manual_token" },
  });
  await syncTikTokAccount(admin, account, { access_token: accessToken, refresh_token: refreshToken || undefined });
  return response(200, { ok: true, platform: "tiktok", accountId: account.id });
}

async function handleChannelAction(event: Event, admin: ReturnType<typeof createAdminClient>, user: any, accountId: string) {
  const body = parseBody(event);
  const action = body.action;
  const { data: account, error } = await admin.from("social_accounts").select("*").eq("id", accountId).single();
  if (error || !account) return response(404, { error: "Channel not found" });
  const membership = await getWorkspaceMembership(admin, account.workspace_id, user.id);
  if (!membership) return response(403, { error: "Forbidden" });

  if (action === "sync") {
    try {
      await syncAccount(admin, account as AccountRow);
      return response(200, { ok: true });
    } catch (syncError: any) {
      await markAccountSyncFailure(admin, accountId, syncError.message || "Sync failed");
      return response(400, { error: syncError.message || "Sync failed" });
    }
  }

  if (action === "reconnect") {
    const state = signedState({
      userId: user.id,
      workspaceId: account.workspace_id,
      platform: account.platform,
      groupId: account.channel_group_id || "",
      ts: String(Date.now()),
    });
    return response(200, { redirect: buildOAuthAuthorizeUrl(account.platform, state) });
  }

  return response(400, { error: "Unsupported action" });
}

async function handleChannelPatch(event: Event, admin: ReturnType<typeof createAdminClient>, user: any, accountId: string) {
  const body = parseBody(event);
  const { data: account, error } = await admin.from("social_accounts").select("*").eq("id", accountId).single();
  if (error || !account) return response(404, { error: "Channel not found" });
  const membership = await getWorkspaceMembership(admin, account.workspace_id, user.id);
  if (!membership) return response(403, { error: "Forbidden" });

  const updates: Record<string, unknown> = {};
  if (body.groupId !== undefined) {
    updates.channel_group_id = body.groupId && body.groupId !== "all" ? body.groupId : null;
  }
  if (body.status) {
    updates.connection_status = body.status;
  }
  if (!Object.keys(updates).length) return response(200, { ok: true });

  const { error: updateError } = await admin.from("social_accounts").update(updates).eq("id", accountId);
  if (updateError) return response(400, { error: updateError.message });
  return response(200, { ok: true });
}

async function handleChannelDelete(event: Event, admin: ReturnType<typeof createAdminClient>, user: any, accountId: string) {
  const { data: account, error } = await admin.from("social_accounts").select("*").eq("id", accountId).single();
  if (error || !account) return response(404, { error: "Channel not found" });
  const membership = await getWorkspaceMembership(admin, account.workspace_id, user.id);
  if (!membership) return response(403, { error: "Forbidden" });
  const { error: deleteError } = await admin.from("social_accounts").delete().eq("id", accountId);
  if (deleteError) return response(400, { error: deleteError.message });
  return response(200, { ok: true });
}

async function handleGroups(event: Event, admin: ReturnType<typeof createAdminClient>, user: any, groupId?: string) {
  const workspace = await ensureWorkspaceForUser(admin, user);
  const body = parseBody(event);

  if (event.httpMethod === "POST") {
    if (!body.name) return response(400, { error: "Group name is required" });
    const { data, error } = await admin
      .from("channel_groups")
      .insert({
        workspace_id: workspace.workspace.id,
        name: String(body.name).trim(),
        description: String(body.description || ""),
        position: Math.max(1, Date.now() % 10000),
      })
      .select("*")
      .single();
    if (error) return response(400, { error: error.message });
    return response(201, { group: data });
  }

  const { data: group, error } = await admin.from("channel_groups").select("*").eq("id", groupId).single();
  if (error || !group) return response(404, { error: "Group not found" });
  const membership = await getWorkspaceMembership(admin, group.workspace_id, user.id);
  if (!membership) return response(403, { error: "Forbidden" });

  if (event.httpMethod === "DELETE") {
    const { error: deleteError } = await admin.from("channel_groups").update({ is_archived: true }).eq("id", groupId);
    if (deleteError) return response(400, { error: deleteError.message });
    return response(200, { ok: true });
  }

  const { error: patchError } = await admin
    .from("channel_groups")
    .update({
      name: body.name ? String(body.name).trim() : group.name,
      description: body.description !== undefined ? String(body.description) : group.description,
    })
    .eq("id", groupId);
  if (patchError) return response(400, { error: patchError.message });
  return response(200, { ok: true });
}

async function handleSettings(event: Event, admin: ReturnType<typeof createAdminClient>, user: any) {
  const body = parseBody(event);
  const notifications = body.notifications || {};
  const profile = body.profile || {};

  await admin.from("user_settings").upsert({
    user_id: user.id,
    email_notifications: notifications.email ?? true,
    push_notifications: notifications.push ?? true,
    alert_notifications: notifications.alerts ?? true,
  });

  if (profile.name) {
    await admin.from("profiles").upsert({
      id: user.id,
      email: user.email,
      full_name: String(profile.name),
    });
  }

  return response(200, { ok: true });
}

const TOKEN_HEALTH_PREFIX = "[TOKEN_HEALTH]";

async function applyTokenHealthStatus(admin: ReturnType<typeof createAdminClient>, account: AccountRow, token: any) {
  const tokenHealth = describeTokenHealth(account, token);
  const warningStatuses = new Set(["expiring", "expiring_refreshable", "expired_refreshable"]);
  const reconnectStatuses = new Set(["expired", "reconnect_required", "missing"]);
  const currentError = String(account.last_error || "");
  const nextMessage = `${TOKEN_HEALTH_PREFIX} ${tokenHealth.description}`;

  if (reconnectStatuses.has(tokenHealth.status)) {
    await admin
      .from("social_accounts")
      .update({
        connection_status: "error",
        last_error: nextMessage,
        last_health_check_at: new Date().toISOString(),
      })
      .eq("id", account.id);
    return { id: account.id, status: tokenHealth.status, severity: "error", changed: true };
  }

  if (warningStatuses.has(tokenHealth.status)) {
    await admin
      .from("social_accounts")
      .update({
        connection_status: account.connection_status === "error" ? account.connection_status : "warning",
        last_error: currentError && !currentError.startsWith(TOKEN_HEALTH_PREFIX) ? currentError : nextMessage,
        last_health_check_at: new Date().toISOString(),
      })
      .eq("id", account.id);
    return { id: account.id, status: tokenHealth.status, severity: "warning", changed: true };
  }

  if (currentError.startsWith(TOKEN_HEALTH_PREFIX) || account.connection_status === "warning") {
    await admin
      .from("social_accounts")
      .update({
        connection_status: "connected",
        last_error: currentError.startsWith(TOKEN_HEALTH_PREFIX) ? "" : currentError,
        last_health_check_at: new Date().toISOString(),
      })
      .eq("id", account.id);
    return { id: account.id, status: tokenHealth.status, severity: "success", changed: true };
  }

  return { id: account.id, status: tokenHealth.status, severity: "success", changed: false };
}

async function handleCronTokenHealth(event: Event, admin: ReturnType<typeof createAdminClient>) {
  const providedSecret = event.headers["x-cron-secret"] || event.headers["X-Cron-Secret"];
  if (!env.cronSecret || providedSecret !== env.cronSecret) {
    return response(401, { error: "Unauthorized" });
  }

  const { data: accounts, error } = await admin.from("social_accounts").select("*");
  if (error) return response(500, { error: error.message });

  const results: Array<{ id: string; status: string; severity: string; changed: boolean; error?: string }> = [];
  for (const account of (accounts || []) as AccountRow[]) {
    try {
      const token = await getTokens(admin, account.id);
      const result = await applyTokenHealthStatus(admin, account, token);
      results.push(result);
    } catch (scanError: any) {
      await admin
        .from("social_accounts")
        .update({
          connection_status: "error",
          last_error: `${TOKEN_HEALTH_PREFIX} ${scanError.message || "Không thể kiểm tra token"}`,
          last_health_check_at: new Date().toISOString(),
        })
        .eq("id", account.id);
      results.push({
        id: account.id,
        status: "scan_failed",
        severity: "error",
        changed: true,
        error: scanError.message || "Token health scan failed",
      });
    }
  }

  return response(200, { scanned: results.length, results });
}

async function handleCronSync(event: Event, admin: ReturnType<typeof createAdminClient>) {
  const providedSecret = event.headers["x-cron-secret"] || event.headers["X-Cron-Secret"];
  if (!env.cronSecret || providedSecret !== env.cronSecret) {
    return response(401, { error: "Unauthorized" });
  }
  const { data: accounts, error } = await admin.from("social_accounts").select("*");
  if (error) return response(500, { error: error.message });
  const results: Array<{ id: string; ok: boolean; error?: string }> = [];
  for (const account of (accounts || []) as AccountRow[]) {
    try {
      await syncAccount(admin, account);
      results.push({ id: account.id, ok: true });
    } catch (syncError: any) {
      await markAccountSyncFailure(admin, account.id, syncError.message || "Sync failed");
      results.push({ id: account.id, ok: false, error: syncError.message || "Sync failed" });
    }
  }
  return response(200, { synced: results.length, results });
}

export async function handler(event: Event) {
  try {
    if (!env.supabaseUrl || !env.supabaseAnonKey || !env.supabaseServiceRoleKey || !env.appUrl || !env.appStateSecret) {
      return response(500, { error: "Missing required environment variables" });
    }

    const path = getPath(event);
    const admin = createAdminClient();

    if (path === "/auth/sign-in" && event.httpMethod === "POST") {
      return handleAuthSignIn(event, admin);
    }

    if (path === "/auth/sign-up" && event.httpMethod === "POST") {
      return handleAuthSignUp(event, admin);
    }

    if (path === "/cron/sync-all" && event.httpMethod === "POST") {
      return handleCronSync(event, admin);
    }

    if (path === "/cron/token-health" && event.httpMethod === "POST") {
      return handleCronTokenHealth(event, admin);
    }

    if (path.startsWith("/oauth/callback/") && event.httpMethod === "GET") {
      return handleOAuthCallback(event, admin);
    }

    const user = await getCurrentUser(event);
    if (!user) {
      return response(401, { error: "Unauthorized" });
    }

    if (path === "/state" && event.httpMethod === "GET") {
      const workspace = await ensureWorkspaceForUser(admin, user);
      const state = await buildStateV2(admin, user, workspace);
      return response(200, state);
    }

    if (path === "/oauth/start" && event.httpMethod === "GET") {
      return handleOAuthStart(event, admin, user);
    }

    if (path === "/channels/import-token" && event.httpMethod === "POST") {
      return handleTokenImport(event, admin, user);
    }

    if (path === "/settings" && event.httpMethod === "PATCH") {
      return handleSettings(event, admin, user);
    }

    if (path === "/groups" && event.httpMethod === "POST") {
      return handleGroups(event, admin, user);
    }

    const groupMatch = path.match(/^\/groups\/([^/]+)$/);
    if (groupMatch && ["PATCH", "DELETE"].includes(event.httpMethod)) {
      return handleGroups(event, admin, user, groupMatch[1]);
    }

    const channelActionMatch = path.match(/^\/channels\/([^/]+)\/action$/);
    if (channelActionMatch && event.httpMethod === "POST") {
      return handleChannelAction(event, admin, user, channelActionMatch[1]);
    }

    const channelMatch = path.match(/^\/channels\/([^/]+)$/);
    if (channelMatch && event.httpMethod === "PATCH") {
      return handleChannelPatch(event, admin, user, channelMatch[1]);
    }
    if (channelMatch && event.httpMethod === "DELETE") {
      return handleChannelDelete(event, admin, user, channelMatch[1]);
    }

    if (
      path === "/posts" ||
      path.startsWith("/posts/") ||
      path === "/media" ||
      path === "/inbox" ||
      path.startsWith("/inbox/") ||
      path === "/members" ||
      path.startsWith("/members/")
    ) {
      return response(501, {
        error: "Tinh nang nay dang phat trien cho phien ban read-only analytics.",
      });
    }

    return response(404, { error: "Not found" });
  } catch (error: any) {
    return response(500, { error: error.message || "Unexpected server error" });
  }
}
