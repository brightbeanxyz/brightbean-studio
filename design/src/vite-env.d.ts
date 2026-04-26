/// <reference types="vite/client" />

interface Window {
  __SOCIAL_MARKETING__?: {
    workspaceId: string;
    workspaceName: string;
    basename: string;
    apiBase: string;
    csrfToken: string;
  };
}
