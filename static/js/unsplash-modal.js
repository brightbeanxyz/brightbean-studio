/**
 * Unsplash Modal — Alpine.js component
 *
 * Manages search, filtering, pagination, and import of Unsplash photos.
 * The component is controlled by an external Alpine component that toggles `show`.
 *
 * Click handling uses document-level event delegation (capture phase)
 * to bypass CSP restrictions on inline handlers and Alpine @click.stop scoping.
 *
 * Parameters are set by the calling Alpine component before opening:
 *   workspaceId - current workspace UUID (required)
 *   apiToken    - DRF auth token for API calls (falls back to window.drfToken)
 *   apiBase     - API base URL (default: '/api/v1/')
 *   onImport    - optional callback when a photo is imported (receives asset data)
 *
 * API Endpoints used:
 *   GET  /api/v1/media/unsplash/search/?q=...&page=...&per_page=20&orientation=...&color=...
 *   POST /api/v1/media/unsplash/import/
 *        Body: {photo_id, workspace_id, folder_id, alt_text, force}
 */
window.unsplashModal = function() {
  return {
    // ── External params (set by caller before open()) ──
    workspaceId: '',
    apiToken: typeof window !== 'undefined' && window.drfToken ? window.drfToken : '',
    apiBase: '/api/v1/',
    onImport: null,

    // ── State ──
    show: false,
    searchQuery: '',
    orientation: '',
    color: '',
    results: [],
    page: 1,
    totalPages: 0,
    totalResults: null,
    loading: false,
    loadingMore: false,
    searched: false,
    error: '',

    get hasResults() {
      return this.results.length > 0 && this.searched;
    },

    // ── Actions ──

    _setupClickDelegation(el) {
      // Document-level capture-phase delegation bypasses
      // CSP (no inline onclick) and @click.stop on modal body.
      var self = this;
      document.addEventListener('click', function(e) {
        var btn = e.target.closest('.import-btn');
        if (!btn) return;
        var photoId = btn.getAttribute('data-import-photo');
        if (!photoId) return;
        e.preventDefault();
        e.stopPropagation();
        var photo = self.results.find(function(p) { return p.id === photoId; });
        if (photo) {
          self.importPhoto(photo);
        }
      }, true);
    },

    open(params) {
      // Reset state
      this.searchQuery = params && params.query ? params.query : '';
      this.orientation = params && params.orientation ? params.orientation : '';
      this.color = params && params.color ? params.color : '';
      this.workspaceId = params && params.workspaceId ? params.workspaceId : '';
      this.results = [];
      this.page = 1;
      this.totalPages = 0;
      this.totalResults = null;
      this.searched = false;
      this.error = '';
      this.show = true;

      // If a query was provided, search immediately
      if (this.searchQuery.trim()) {
        var self = this;
        this.$nextTick(function() { self.search(); });
      }
    },

    close() {
      this.show = false;
    },

    search() {
      var query = this.searchQuery.trim();
      if (!query) return;

      this.loading = true;
      this.error = '';
      this.page = 1;
      this.results = [];
      this.totalPages = 0;
      this.totalResults = null;
      this.searched = true;

      this._fetchResults();
    },

    loadMore() {
      if (this.loadingMore || this.page >= this.totalPages) return;
      this.page++;
      this.loadingMore = true;

      this._fetchResults(true);
    },

    _fetchResults(append) {
      append = append || false;
      var query = this.searchQuery.trim();
      if (!query) return;

      var url = this.apiBase + 'media/unsplash/search/?q=' + encodeURIComponent(query) +
                '&page=' + this.page + '&per_page=20';
      if (this.orientation) url += '&orientation=' + encodeURIComponent(this.orientation);
      if (this.color) url += '&color=' + encodeURIComponent(this.color);

      var headers = {};
      if (this.apiToken) {
        headers['Authorization'] = 'Token ' + this.apiToken;
      }

      var self = this;
      fetch(url, { headers: headers })
        .then(function(r) {
          if (!r.ok) {
            return r.json().then(function(data) { return Promise.reject(data); });
          }
          return r.json();
        })
        .then(function(data) {
          if (append) {
            self.results = self.results.concat(data.results || []);
          } else {
            self.results = data.results || [];
          }
          self.totalResults = data.total || self.results.length;
          self.totalPages = data.total_pages || 1;
        })
        .catch(function(err) {
          self.error = (err && err.error) || 'Failed to search Unsplash. Please try again.';
          if (!append) self.searched = true;
        })
        .finally(function() {
          self.loading = false;
          self.loadingMore = false;
        });
    },

    importPhoto(photo) {
      if (photo._importing || photo._imported) return;

      photo._importing = true;

      var body = {
        photo_id: photo.id,
        workspace_id: this.workspaceId,
        folder_id: null,
        alt_text: photo.description || '',
        force: false
      };

      var headers = {
        'Content-Type': 'application/json'
      };
      if (this.apiToken) {
        headers['Authorization'] = 'Token ' + this.apiToken;
      }

      var self = this;
      fetch(this.apiBase + 'media/unsplash/import/', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(body)
      })
        .then(function(r) {
          if (r.status === 409) {
            // Dedup — show already-imported state
            photo._duplicate = true;
            setTimeout(function() { photo._duplicate = false; }, 2000);
            return null;
          }
          if (!r.ok) {
            return r.json().then(function(data) { return Promise.reject(data); });
          }
          return r.json();
        })
        .then(function(data) {
          if (data) {
            photo._imported = true;
            if (typeof self.onImport === 'function') {
              self.onImport(data);
            }
            // Refresh the media library asset grid if present
            var grid = document.getElementById('asset-grid');
            if (grid && typeof htmx !== 'undefined') {
              htmx.trigger(grid, 'uploadsComplete');
            }
            setTimeout(function() { photo._imported = false; }, 3000);
          }
        })
        .catch(function(err) {
          self.error = (err && err.error) || 'Failed to import photo. Please try again.';
        })
        .finally(function() {
          photo._importing = false;
        });
    }
  };
};
