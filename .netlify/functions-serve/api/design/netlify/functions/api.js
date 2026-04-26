var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __esm = (fn, res) => function __init() {
  return fn && (res = (0, fn[__getOwnPropNames(fn)[0]])(fn = 0)), res;
};
var __commonJS = (cb, mod) => function __require() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __reExport = (target, mod, secondTarget) => (__copyProps(target, mod, "default"), secondTarget && __copyProps(secondTarget, mod, "default"));
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// design/node_modules/tslib/tslib.es6.mjs
var tslib_es6_exports = {};
__export(tslib_es6_exports, {
  __addDisposableResource: () => __addDisposableResource,
  __assign: () => __assign,
  __asyncDelegator: () => __asyncDelegator,
  __asyncGenerator: () => __asyncGenerator,
  __asyncValues: () => __asyncValues,
  __await: () => __await,
  __awaiter: () => __awaiter,
  __classPrivateFieldGet: () => __classPrivateFieldGet,
  __classPrivateFieldIn: () => __classPrivateFieldIn,
  __classPrivateFieldSet: () => __classPrivateFieldSet,
  __createBinding: () => __createBinding,
  __decorate: () => __decorate,
  __disposeResources: () => __disposeResources,
  __esDecorate: () => __esDecorate,
  __exportStar: () => __exportStar,
  __extends: () => __extends,
  __generator: () => __generator,
  __importDefault: () => __importDefault,
  __importStar: () => __importStar,
  __makeTemplateObject: () => __makeTemplateObject,
  __metadata: () => __metadata,
  __param: () => __param,
  __propKey: () => __propKey,
  __read: () => __read,
  __rest: () => __rest,
  __rewriteRelativeImportExtension: () => __rewriteRelativeImportExtension,
  __runInitializers: () => __runInitializers,
  __setFunctionName: () => __setFunctionName,
  __spread: () => __spread,
  __spreadArray: () => __spreadArray,
  __spreadArrays: () => __spreadArrays,
  __values: () => __values,
  default: () => tslib_es6_default
});
function __extends(d, b) {
  if (typeof b !== "function" && b !== null)
    throw new TypeError("Class extends value " + String(b) + " is not a constructor or null");
  extendStatics(d, b);
  function __() {
    this.constructor = d;
  }
  d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
}
function __rest(s, e) {
  var t = {};
  for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
    t[p] = s[p];
  if (s != null && typeof Object.getOwnPropertySymbols === "function")
    for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
      if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i]))
        t[p[i]] = s[p[i]];
    }
  return t;
}
function __decorate(decorators, target, key, desc) {
  var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
  else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
  return c > 3 && r && Object.defineProperty(target, key, r), r;
}
function __param(paramIndex, decorator) {
  return function(target, key) {
    decorator(target, key, paramIndex);
  };
}
function __esDecorate(ctor, descriptorIn, decorators, contextIn, initializers, extraInitializers) {
  function accept(f) {
    if (f !== void 0 && typeof f !== "function") throw new TypeError("Function expected");
    return f;
  }
  var kind = contextIn.kind, key = kind === "getter" ? "get" : kind === "setter" ? "set" : "value";
  var target = !descriptorIn && ctor ? contextIn["static"] ? ctor : ctor.prototype : null;
  var descriptor = descriptorIn || (target ? Object.getOwnPropertyDescriptor(target, contextIn.name) : {});
  var _, done = false;
  for (var i = decorators.length - 1; i >= 0; i--) {
    var context = {};
    for (var p in contextIn) context[p] = p === "access" ? {} : contextIn[p];
    for (var p in contextIn.access) context.access[p] = contextIn.access[p];
    context.addInitializer = function(f) {
      if (done) throw new TypeError("Cannot add initializers after decoration has completed");
      extraInitializers.push(accept(f || null));
    };
    var result = (0, decorators[i])(kind === "accessor" ? { get: descriptor.get, set: descriptor.set } : descriptor[key], context);
    if (kind === "accessor") {
      if (result === void 0) continue;
      if (result === null || typeof result !== "object") throw new TypeError("Object expected");
      if (_ = accept(result.get)) descriptor.get = _;
      if (_ = accept(result.set)) descriptor.set = _;
      if (_ = accept(result.init)) initializers.unshift(_);
    } else if (_ = accept(result)) {
      if (kind === "field") initializers.unshift(_);
      else descriptor[key] = _;
    }
  }
  if (target) Object.defineProperty(target, contextIn.name, descriptor);
  done = true;
}
function __runInitializers(thisArg, initializers, value) {
  var useValue = arguments.length > 2;
  for (var i = 0; i < initializers.length; i++) {
    value = useValue ? initializers[i].call(thisArg, value) : initializers[i].call(thisArg);
  }
  return useValue ? value : void 0;
}
function __propKey(x) {
  return typeof x === "symbol" ? x : "".concat(x);
}
function __setFunctionName(f, name, prefix) {
  if (typeof name === "symbol") name = name.description ? "[".concat(name.description, "]") : "";
  return Object.defineProperty(f, "name", { configurable: true, value: prefix ? "".concat(prefix, " ", name) : name });
}
function __metadata(metadataKey, metadataValue) {
  if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(metadataKey, metadataValue);
}
function __awaiter(thisArg, _arguments, P, generator) {
  function adopt(value) {
    return value instanceof P ? value : new P(function(resolve) {
      resolve(value);
    });
  }
  return new (P || (P = Promise))(function(resolve, reject) {
    function fulfilled(value) {
      try {
        step(generator.next(value));
      } catch (e) {
        reject(e);
      }
    }
    function rejected(value) {
      try {
        step(generator["throw"](value));
      } catch (e) {
        reject(e);
      }
    }
    function step(result) {
      result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected);
    }
    step((generator = generator.apply(thisArg, _arguments || [])).next());
  });
}
function __generator(thisArg, body) {
  var _ = { label: 0, sent: function() {
    if (t[0] & 1) throw t[1];
    return t[1];
  }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
  return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() {
    return this;
  }), g;
  function verb(n) {
    return function(v) {
      return step([n, v]);
    };
  }
  function step(op) {
    if (f) throw new TypeError("Generator is already executing.");
    while (g && (g = 0, op[0] && (_ = 0)), _) try {
      if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
      if (y = 0, t) op = [op[0] & 2, t.value];
      switch (op[0]) {
        case 0:
        case 1:
          t = op;
          break;
        case 4:
          _.label++;
          return { value: op[1], done: false };
        case 5:
          _.label++;
          y = op[1];
          op = [0];
          continue;
        case 7:
          op = _.ops.pop();
          _.trys.pop();
          continue;
        default:
          if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) {
            _ = 0;
            continue;
          }
          if (op[0] === 3 && (!t || op[1] > t[0] && op[1] < t[3])) {
            _.label = op[1];
            break;
          }
          if (op[0] === 6 && _.label < t[1]) {
            _.label = t[1];
            t = op;
            break;
          }
          if (t && _.label < t[2]) {
            _.label = t[2];
            _.ops.push(op);
            break;
          }
          if (t[2]) _.ops.pop();
          _.trys.pop();
          continue;
      }
      op = body.call(thisArg, _);
    } catch (e) {
      op = [6, e];
      y = 0;
    } finally {
      f = t = 0;
    }
    if (op[0] & 5) throw op[1];
    return { value: op[0] ? op[1] : void 0, done: true };
  }
}
function __exportStar(m, o) {
  for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(o, p)) __createBinding(o, m, p);
}
function __values(o) {
  var s = typeof Symbol === "function" && Symbol.iterator, m = s && o[s], i = 0;
  if (m) return m.call(o);
  if (o && typeof o.length === "number") return {
    next: function() {
      if (o && i >= o.length) o = void 0;
      return { value: o && o[i++], done: !o };
    }
  };
  throw new TypeError(s ? "Object is not iterable." : "Symbol.iterator is not defined.");
}
function __read(o, n) {
  var m = typeof Symbol === "function" && o[Symbol.iterator];
  if (!m) return o;
  var i = m.call(o), r, ar = [], e;
  try {
    while ((n === void 0 || n-- > 0) && !(r = i.next()).done) ar.push(r.value);
  } catch (error) {
    e = { error };
  } finally {
    try {
      if (r && !r.done && (m = i["return"])) m.call(i);
    } finally {
      if (e) throw e.error;
    }
  }
  return ar;
}
function __spread() {
  for (var ar = [], i = 0; i < arguments.length; i++)
    ar = ar.concat(__read(arguments[i]));
  return ar;
}
function __spreadArrays() {
  for (var s = 0, i = 0, il = arguments.length; i < il; i++) s += arguments[i].length;
  for (var r = Array(s), k = 0, i = 0; i < il; i++)
    for (var a = arguments[i], j = 0, jl = a.length; j < jl; j++, k++)
      r[k] = a[j];
  return r;
}
function __spreadArray(to, from, pack) {
  if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
    if (ar || !(i in from)) {
      if (!ar) ar = Array.prototype.slice.call(from, 0, i);
      ar[i] = from[i];
    }
  }
  return to.concat(ar || Array.prototype.slice.call(from));
}
function __await(v) {
  return this instanceof __await ? (this.v = v, this) : new __await(v);
}
function __asyncGenerator(thisArg, _arguments, generator) {
  if (!Symbol.asyncIterator) throw new TypeError("Symbol.asyncIterator is not defined.");
  var g = generator.apply(thisArg, _arguments || []), i, q = [];
  return i = Object.create((typeof AsyncIterator === "function" ? AsyncIterator : Object).prototype), verb("next"), verb("throw"), verb("return", awaitReturn), i[Symbol.asyncIterator] = function() {
    return this;
  }, i;
  function awaitReturn(f) {
    return function(v) {
      return Promise.resolve(v).then(f, reject);
    };
  }
  function verb(n, f) {
    if (g[n]) {
      i[n] = function(v) {
        return new Promise(function(a, b) {
          q.push([n, v, a, b]) > 1 || resume(n, v);
        });
      };
      if (f) i[n] = f(i[n]);
    }
  }
  function resume(n, v) {
    try {
      step(g[n](v));
    } catch (e) {
      settle(q[0][3], e);
    }
  }
  function step(r) {
    r.value instanceof __await ? Promise.resolve(r.value.v).then(fulfill, reject) : settle(q[0][2], r);
  }
  function fulfill(value) {
    resume("next", value);
  }
  function reject(value) {
    resume("throw", value);
  }
  function settle(f, v) {
    if (f(v), q.shift(), q.length) resume(q[0][0], q[0][1]);
  }
}
function __asyncDelegator(o) {
  var i, p;
  return i = {}, verb("next"), verb("throw", function(e) {
    throw e;
  }), verb("return"), i[Symbol.iterator] = function() {
    return this;
  }, i;
  function verb(n, f) {
    i[n] = o[n] ? function(v) {
      return (p = !p) ? { value: __await(o[n](v)), done: false } : f ? f(v) : v;
    } : f;
  }
}
function __asyncValues(o) {
  if (!Symbol.asyncIterator) throw new TypeError("Symbol.asyncIterator is not defined.");
  var m = o[Symbol.asyncIterator], i;
  return m ? m.call(o) : (o = typeof __values === "function" ? __values(o) : o[Symbol.iterator](), i = {}, verb("next"), verb("throw"), verb("return"), i[Symbol.asyncIterator] = function() {
    return this;
  }, i);
  function verb(n) {
    i[n] = o[n] && function(v) {
      return new Promise(function(resolve, reject) {
        v = o[n](v), settle(resolve, reject, v.done, v.value);
      });
    };
  }
  function settle(resolve, reject, d, v) {
    Promise.resolve(v).then(function(v2) {
      resolve({ value: v2, done: d });
    }, reject);
  }
}
function __makeTemplateObject(cooked, raw) {
  if (Object.defineProperty) {
    Object.defineProperty(cooked, "raw", { value: raw });
  } else {
    cooked.raw = raw;
  }
  return cooked;
}
function __importStar(mod) {
  if (mod && mod.__esModule) return mod;
  var result = {};
  if (mod != null) {
    for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
  }
  __setModuleDefault(result, mod);
  return result;
}
function __importDefault(mod) {
  return mod && mod.__esModule ? mod : { default: mod };
}
function __classPrivateFieldGet(receiver, state, kind, f) {
  if (kind === "a" && !f) throw new TypeError("Private accessor was defined without a getter");
  if (typeof state === "function" ? receiver !== state || !f : !state.has(receiver)) throw new TypeError("Cannot read private member from an object whose class did not declare it");
  return kind === "m" ? f : kind === "a" ? f.call(receiver) : f ? f.value : state.get(receiver);
}
function __classPrivateFieldSet(receiver, state, value, kind, f) {
  if (kind === "m") throw new TypeError("Private method is not writable");
  if (kind === "a" && !f) throw new TypeError("Private accessor was defined without a setter");
  if (typeof state === "function" ? receiver !== state || !f : !state.has(receiver)) throw new TypeError("Cannot write private member to an object whose class did not declare it");
  return kind === "a" ? f.call(receiver, value) : f ? f.value = value : state.set(receiver, value), value;
}
function __classPrivateFieldIn(state, receiver) {
  if (receiver === null || typeof receiver !== "object" && typeof receiver !== "function") throw new TypeError("Cannot use 'in' operator on non-object");
  return typeof state === "function" ? receiver === state : state.has(receiver);
}
function __addDisposableResource(env2, value, async) {
  if (value !== null && value !== void 0) {
    if (typeof value !== "object" && typeof value !== "function") throw new TypeError("Object expected.");
    var dispose, inner;
    if (async) {
      if (!Symbol.asyncDispose) throw new TypeError("Symbol.asyncDispose is not defined.");
      dispose = value[Symbol.asyncDispose];
    }
    if (dispose === void 0) {
      if (!Symbol.dispose) throw new TypeError("Symbol.dispose is not defined.");
      dispose = value[Symbol.dispose];
      if (async) inner = dispose;
    }
    if (typeof dispose !== "function") throw new TypeError("Object not disposable.");
    if (inner) dispose = function() {
      try {
        inner.call(this);
      } catch (e) {
        return Promise.reject(e);
      }
    };
    env2.stack.push({ value, dispose, async });
  } else if (async) {
    env2.stack.push({ async: true });
  }
  return value;
}
function __disposeResources(env2) {
  function fail(e) {
    env2.error = env2.hasError ? new _SuppressedError(e, env2.error, "An error was suppressed during disposal.") : e;
    env2.hasError = true;
  }
  var r, s = 0;
  function next() {
    while (r = env2.stack.pop()) {
      try {
        if (!r.async && s === 1) return s = 0, env2.stack.push(r), Promise.resolve().then(next);
        if (r.dispose) {
          var result = r.dispose.call(r.value);
          if (r.async) return s |= 2, Promise.resolve(result).then(next, function(e) {
            fail(e);
            return next();
          });
        } else s |= 1;
      } catch (e) {
        fail(e);
      }
    }
    if (s === 1) return env2.hasError ? Promise.reject(env2.error) : Promise.resolve();
    if (env2.hasError) throw env2.error;
  }
  return next();
}
function __rewriteRelativeImportExtension(path, preserveJsx) {
  if (typeof path === "string" && /^\.\.?\//.test(path)) {
    return path.replace(/\.(tsx)$|((?:\.d)?)((?:\.[^./]+?)?)\.([cm]?)ts$/i, function(m, tsx, d, ext, cm) {
      return tsx ? preserveJsx ? ".jsx" : ".js" : d && (!ext || !cm) ? m : d + ext + "." + cm.toLowerCase() + "js";
    });
  }
  return path;
}
var extendStatics, __assign, __createBinding, __setModuleDefault, ownKeys, _SuppressedError, tslib_es6_default;
var init_tslib_es6 = __esm({
  "design/node_modules/tslib/tslib.es6.mjs"() {
    extendStatics = function(d, b) {
      extendStatics = Object.setPrototypeOf || { __proto__: [] } instanceof Array && function(d2, b2) {
        d2.__proto__ = b2;
      } || function(d2, b2) {
        for (var p in b2) if (Object.prototype.hasOwnProperty.call(b2, p)) d2[p] = b2[p];
      };
      return extendStatics(d, b);
    };
    __assign = function() {
      __assign = Object.assign || function __assign2(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
          s = arguments[i];
          for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p)) t[p] = s[p];
        }
        return t;
      };
      return __assign.apply(this, arguments);
    };
    __createBinding = Object.create ? (function(o, m, k, k2) {
      if (k2 === void 0) k2 = k;
      var desc = Object.getOwnPropertyDescriptor(m, k);
      if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
        desc = { enumerable: true, get: function() {
          return m[k];
        } };
      }
      Object.defineProperty(o, k2, desc);
    }) : (function(o, m, k, k2) {
      if (k2 === void 0) k2 = k;
      o[k2] = m[k];
    });
    __setModuleDefault = Object.create ? (function(o, v) {
      Object.defineProperty(o, "default", { enumerable: true, value: v });
    }) : function(o, v) {
      o["default"] = v;
    };
    ownKeys = function(o) {
      ownKeys = Object.getOwnPropertyNames || function(o2) {
        var ar = [];
        for (var k in o2) if (Object.prototype.hasOwnProperty.call(o2, k)) ar[ar.length] = k;
        return ar;
      };
      return ownKeys(o);
    };
    _SuppressedError = typeof SuppressedError === "function" ? SuppressedError : function(error, suppressed, message) {
      var e = new Error(message);
      return e.name = "SuppressedError", e.error = error, e.suppressed = suppressed, e;
    };
    tslib_es6_default = {
      __extends,
      __assign,
      __rest,
      __decorate,
      __param,
      __esDecorate,
      __runInitializers,
      __propKey,
      __setFunctionName,
      __metadata,
      __awaiter,
      __generator,
      __createBinding,
      __exportStar,
      __values,
      __read,
      __spread,
      __spreadArrays,
      __spreadArray,
      __await,
      __asyncGenerator,
      __asyncDelegator,
      __asyncValues,
      __makeTemplateObject,
      __importStar,
      __importDefault,
      __classPrivateFieldGet,
      __classPrivateFieldSet,
      __classPrivateFieldIn,
      __addDisposableResource,
      __disposeResources,
      __rewriteRelativeImportExtension
    };
  }
});

// design/node_modules/@supabase/functions-js/dist/main/helper.js
var require_helper = __commonJS({
  "design/node_modules/@supabase/functions-js/dist/main/helper.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.resolveFetch = void 0;
    var resolveFetch3 = (customFetch) => {
      if (customFetch) {
        return (...args) => customFetch(...args);
      }
      return (...args) => fetch(...args);
    };
    exports2.resolveFetch = resolveFetch3;
  }
});

// design/node_modules/@supabase/functions-js/dist/main/types.js
var require_types = __commonJS({
  "design/node_modules/@supabase/functions-js/dist/main/types.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.FunctionRegion = exports2.FunctionsHttpError = exports2.FunctionsRelayError = exports2.FunctionsFetchError = exports2.FunctionsError = void 0;
    var FunctionsError2 = class extends Error {
      constructor(message, name = "FunctionsError", context) {
        super(message);
        this.name = name;
        this.context = context;
      }
      toJSON() {
        return {
          name: this.name,
          message: this.message,
          context: this.context
        };
      }
    };
    exports2.FunctionsError = FunctionsError2;
    var FunctionsFetchError2 = class extends FunctionsError2 {
      constructor(context) {
        super("Failed to send a request to the Edge Function", "FunctionsFetchError", context);
      }
    };
    exports2.FunctionsFetchError = FunctionsFetchError2;
    var FunctionsRelayError2 = class extends FunctionsError2 {
      constructor(context) {
        super("Relay Error invoking the Edge Function", "FunctionsRelayError", context);
      }
    };
    exports2.FunctionsRelayError = FunctionsRelayError2;
    var FunctionsHttpError2 = class extends FunctionsError2 {
      constructor(context) {
        super("Edge Function returned a non-2xx status code", "FunctionsHttpError", context);
      }
    };
    exports2.FunctionsHttpError = FunctionsHttpError2;
    var FunctionRegion2;
    (function(FunctionRegion3) {
      FunctionRegion3["Any"] = "any";
      FunctionRegion3["ApNortheast1"] = "ap-northeast-1";
      FunctionRegion3["ApNortheast2"] = "ap-northeast-2";
      FunctionRegion3["ApSouth1"] = "ap-south-1";
      FunctionRegion3["ApSoutheast1"] = "ap-southeast-1";
      FunctionRegion3["ApSoutheast2"] = "ap-southeast-2";
      FunctionRegion3["CaCentral1"] = "ca-central-1";
      FunctionRegion3["EuCentral1"] = "eu-central-1";
      FunctionRegion3["EuWest1"] = "eu-west-1";
      FunctionRegion3["EuWest2"] = "eu-west-2";
      FunctionRegion3["EuWest3"] = "eu-west-3";
      FunctionRegion3["SaEast1"] = "sa-east-1";
      FunctionRegion3["UsEast1"] = "us-east-1";
      FunctionRegion3["UsWest1"] = "us-west-1";
      FunctionRegion3["UsWest2"] = "us-west-2";
    })(FunctionRegion2 || (exports2.FunctionRegion = FunctionRegion2 = {}));
  }
});

// design/node_modules/@supabase/functions-js/dist/main/FunctionsClient.js
var require_FunctionsClient = __commonJS({
  "design/node_modules/@supabase/functions-js/dist/main/FunctionsClient.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.FunctionsClient = void 0;
    var tslib_1 = (init_tslib_es6(), __toCommonJS(tslib_es6_exports));
    var helper_1 = require_helper();
    var types_1 = require_types();
    var FunctionsClient2 = class {
      /**
       * Creates a new Functions client bound to an Edge Functions URL.
       *
       * @example Using supabase-js (recommended)
       * ```ts
       * import { createClient } from '@supabase/supabase-js'
       *
       * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key')
       * const { data, error } = await supabase.functions.invoke('hello-world')
       * ```
       *
       * @category Functions
       *
       * @example Standalone import for bundle-sensitive environments
       * ```ts
       * import { FunctionsClient, FunctionRegion } from '@supabase/functions-js'
       *
       * const functions = new FunctionsClient('https://xyzcompany.supabase.co/functions/v1', {
       *   headers: { apikey: 'publishable-or-anon-key' },
       *   region: FunctionRegion.UsEast1,
       * })
       * ```
       */
      constructor(url, { headers = {}, customFetch, region = types_1.FunctionRegion.Any } = {}) {
        this.url = url;
        this.headers = headers;
        this.region = region;
        this.fetch = (0, helper_1.resolveFetch)(customFetch);
      }
      /**
       * Updates the authorization header
       * @param token - the new jwt token sent in the authorisation header
       *
       * @category Functions
       *
       * @example Setting the authorization header
       * ```ts
       * functions.setAuth(session.access_token)
       * ```
       */
      setAuth(token) {
        this.headers.Authorization = `Bearer ${token}`;
      }
      /**
       * Invokes a function
       * @param functionName - The name of the Function to invoke.
       * @param options - Options for invoking the Function.
       * @example
       * ```ts
       * const { data, error } = await functions.invoke('hello-world', {
       *   body: { name: 'Ada' },
       * })
       * ```
       *
       * @category Functions
       *
       * @remarks
       * - Requires an Authorization header.
       * - Invoke params generally match the [Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API) spec.
       * - When you pass in a body to your function, we automatically attach the Content-Type header for `Blob`, `ArrayBuffer`, `File`, `FormData` and `String`. If it doesn't match any of these types we assume the payload is `json`, serialize it and attach the `Content-Type` header as `application/json`. You can override this behavior by passing in a `Content-Type` header of your own.
       * - Responses are automatically parsed as `json`, `blob` and `form-data` depending on the `Content-Type` header sent by your function. Responses are parsed as `text` by default.
       *
       * @example Basic invocation
       * ```js
       * const { data, error } = await supabase.functions.invoke('hello', {
       *   body: { foo: 'bar' }
       * })
       * ```
       *
       * @exampleDescription Error handling
       * A `FunctionsHttpError` error is returned if your function throws an error, `FunctionsRelayError` if the Supabase Relay has an error processing your function and `FunctionsFetchError` if there is a network error in calling your function.
       *
       * @example Error handling
       * ```js
       * import { FunctionsHttpError, FunctionsRelayError, FunctionsFetchError } from "@supabase/supabase-js";
       *
       * const { data, error } = await supabase.functions.invoke('hello', {
       *   headers: {
       *     "my-custom-header": 'my-custom-header-value'
       *   },
       *   body: { foo: 'bar' }
       * })
       *
       * if (error instanceof FunctionsHttpError) {
       *   const errorMessage = await error.context.json()
       *   console.log('Function returned an error', errorMessage)
       * } else if (error instanceof FunctionsRelayError) {
       *   console.log('Relay error:', error.message)
       * } else if (error instanceof FunctionsFetchError) {
       *   console.log('Fetch error:', error.message)
       * }
       * ```
       *
       * @exampleDescription Passing custom headers
       * You can pass custom headers to your function. Note: supabase-js automatically passes the `Authorization` header with the signed in user's JWT.
       *
       * @example Passing custom headers
       * ```js
       * const { data, error } = await supabase.functions.invoke('hello', {
       *   headers: {
       *     "my-custom-header": 'my-custom-header-value'
       *   },
       *   body: { foo: 'bar' }
       * })
       * ```
       *
       * @exampleDescription Calling with DELETE HTTP verb
       * You can also set the HTTP verb to `DELETE` when calling your Edge Function.
       *
       * @example Calling with DELETE HTTP verb
       * ```js
       * const { data, error } = await supabase.functions.invoke('hello', {
       *   headers: {
       *     "my-custom-header": 'my-custom-header-value'
       *   },
       *   body: { foo: 'bar' },
       *   method: 'DELETE'
       * })
       * ```
       *
       * @exampleDescription Invoking a Function in the UsEast1 region
       * Here are the available regions:
       * - `FunctionRegion.Any`
       * - `FunctionRegion.ApNortheast1`
       * - `FunctionRegion.ApNortheast2`
       * - `FunctionRegion.ApSouth1`
       * - `FunctionRegion.ApSoutheast1`
       * - `FunctionRegion.ApSoutheast2`
       * - `FunctionRegion.CaCentral1`
       * - `FunctionRegion.EuCentral1`
       * - `FunctionRegion.EuWest1`
       * - `FunctionRegion.EuWest2`
       * - `FunctionRegion.EuWest3`
       * - `FunctionRegion.SaEast1`
       * - `FunctionRegion.UsEast1`
       * - `FunctionRegion.UsWest1`
       * - `FunctionRegion.UsWest2`
       *
       * @example Invoking a Function in the UsEast1 region
       * ```js
       * import { createClient, FunctionRegion } from '@supabase/supabase-js'
       *
       * const { data, error } = await supabase.functions.invoke('hello', {
       *   body: { foo: 'bar' },
       *   region: FunctionRegion.UsEast1
       * })
       * ```
       *
       * @exampleDescription Calling with GET HTTP verb
       * You can also set the HTTP verb to `GET` when calling your Edge Function.
       *
       * @example Calling with GET HTTP verb
       * ```js
       * const { data, error } = await supabase.functions.invoke('hello', {
       *   headers: {
       *     "my-custom-header": 'my-custom-header-value'
       *   },
       *   method: 'GET'
       * })
       * ```
       *
       * @example Example 7
       * ```ts
       * const { data, error } = await functions.invoke('hello-world', {
       *   body: { name: 'Ada' },
       * })
       * ```
       */
      invoke(functionName_1) {
        return tslib_1.__awaiter(this, arguments, void 0, function* (functionName, options = {}) {
          var _a;
          let timeoutId;
          let timeoutController;
          try {
            const { headers, method, body: functionArgs, signal, timeout } = options;
            let _headers = {};
            let { region } = options;
            if (!region) {
              region = this.region;
            }
            const url = new URL(`${this.url}/${functionName}`);
            if (region && region !== "any") {
              _headers["x-region"] = region;
              url.searchParams.set("forceFunctionRegion", region);
            }
            let body;
            if (functionArgs && (headers && !Object.prototype.hasOwnProperty.call(headers, "Content-Type") || !headers)) {
              if (typeof Blob !== "undefined" && functionArgs instanceof Blob || functionArgs instanceof ArrayBuffer) {
                _headers["Content-Type"] = "application/octet-stream";
                body = functionArgs;
              } else if (typeof functionArgs === "string") {
                _headers["Content-Type"] = "text/plain";
                body = functionArgs;
              } else if (typeof FormData !== "undefined" && functionArgs instanceof FormData) {
                body = functionArgs;
              } else {
                _headers["Content-Type"] = "application/json";
                body = JSON.stringify(functionArgs);
              }
            } else {
              if (functionArgs && typeof functionArgs !== "string" && !(typeof Blob !== "undefined" && functionArgs instanceof Blob) && !(functionArgs instanceof ArrayBuffer) && !(typeof FormData !== "undefined" && functionArgs instanceof FormData)) {
                body = JSON.stringify(functionArgs);
              } else {
                body = functionArgs;
              }
            }
            let effectiveSignal = signal;
            if (timeout) {
              timeoutController = new AbortController();
              timeoutId = setTimeout(() => timeoutController.abort(), timeout);
              if (signal) {
                effectiveSignal = timeoutController.signal;
                signal.addEventListener("abort", () => timeoutController.abort());
              } else {
                effectiveSignal = timeoutController.signal;
              }
            }
            const response2 = yield this.fetch(url.toString(), {
              method: method || "POST",
              // headers priority is (high to low):
              // 1. invoke-level headers
              // 2. client-level headers
              // 3. default Content-Type header
              headers: Object.assign(Object.assign(Object.assign({}, _headers), this.headers), headers),
              body,
              signal: effectiveSignal
            }).catch((fetchError) => {
              throw new types_1.FunctionsFetchError(fetchError);
            });
            const isRelayError = response2.headers.get("x-relay-error");
            if (isRelayError && isRelayError === "true") {
              throw new types_1.FunctionsRelayError(response2);
            }
            if (!response2.ok) {
              throw new types_1.FunctionsHttpError(response2);
            }
            let responseType = ((_a = response2.headers.get("Content-Type")) !== null && _a !== void 0 ? _a : "text/plain").split(";")[0].trim();
            let data;
            if (responseType === "application/json") {
              data = yield response2.json();
            } else if (responseType === "application/octet-stream" || responseType === "application/pdf") {
              data = yield response2.blob();
            } else if (responseType === "text/event-stream") {
              data = response2;
            } else if (responseType === "multipart/form-data") {
              data = yield response2.formData();
            } else {
              data = yield response2.text();
            }
            return { data, error: null, response: response2 };
          } catch (error) {
            return {
              data: null,
              error,
              response: error instanceof types_1.FunctionsHttpError || error instanceof types_1.FunctionsRelayError ? error.context : void 0
            };
          } finally {
            if (timeoutId) {
              clearTimeout(timeoutId);
            }
          }
        });
      }
    };
    exports2.FunctionsClient = FunctionsClient2;
  }
});

// design/node_modules/@supabase/functions-js/dist/main/index.js
var require_main = __commonJS({
  "design/node_modules/@supabase/functions-js/dist/main/index.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.FunctionRegion = exports2.FunctionsRelayError = exports2.FunctionsHttpError = exports2.FunctionsFetchError = exports2.FunctionsError = exports2.FunctionsClient = void 0;
    var FunctionsClient_1 = require_FunctionsClient();
    Object.defineProperty(exports2, "FunctionsClient", { enumerable: true, get: function() {
      return FunctionsClient_1.FunctionsClient;
    } });
    var types_1 = require_types();
    Object.defineProperty(exports2, "FunctionsError", { enumerable: true, get: function() {
      return types_1.FunctionsError;
    } });
    Object.defineProperty(exports2, "FunctionsFetchError", { enumerable: true, get: function() {
      return types_1.FunctionsFetchError;
    } });
    Object.defineProperty(exports2, "FunctionsHttpError", { enumerable: true, get: function() {
      return types_1.FunctionsHttpError;
    } });
    Object.defineProperty(exports2, "FunctionsRelayError", { enumerable: true, get: function() {
      return types_1.FunctionsRelayError;
    } });
    Object.defineProperty(exports2, "FunctionRegion", { enumerable: true, get: function() {
      return types_1.FunctionRegion;
    } });
  }
});

// design/node_modules/@supabase/realtime-js/dist/main/lib/websocket-factory.js
var require_websocket_factory = __commonJS({
  "design/node_modules/@supabase/realtime-js/dist/main/lib/websocket-factory.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.WebSocketFactory = void 0;
    var WebSocketFactory = class {
      /**
       * Static-only utility – prevent instantiation.
       */
      constructor() {
      }
      static detectEnvironment() {
        var _a;
        if (typeof WebSocket !== "undefined") {
          return { type: "native", constructor: WebSocket };
        }
        if (typeof globalThis !== "undefined" && typeof globalThis.WebSocket !== "undefined") {
          return { type: "native", constructor: globalThis.WebSocket };
        }
        if (typeof global !== "undefined" && typeof global.WebSocket !== "undefined") {
          return { type: "native", constructor: global.WebSocket };
        }
        if (typeof globalThis !== "undefined" && typeof globalThis.WebSocketPair !== "undefined" && typeof globalThis.WebSocket === "undefined") {
          return {
            type: "cloudflare",
            error: "Cloudflare Workers detected. WebSocket clients are not supported in Cloudflare Workers.",
            workaround: "Use Cloudflare Workers WebSocket API for server-side WebSocket handling, or deploy to a different runtime."
          };
        }
        if (typeof globalThis !== "undefined" && globalThis.EdgeRuntime || typeof navigator !== "undefined" && ((_a = navigator.userAgent) === null || _a === void 0 ? void 0 : _a.includes("Vercel-Edge"))) {
          return {
            type: "unsupported",
            error: "Edge runtime detected (Vercel Edge/Netlify Edge). WebSockets are not supported in edge functions.",
            workaround: "Use serverless functions or a different deployment target for WebSocket functionality."
          };
        }
        const _process = globalThis["process"];
        if (_process) {
          const processVersions = _process["versions"];
          if (processVersions && processVersions["node"]) {
            const versionString = processVersions["node"];
            const nodeVersion = parseInt(versionString.replace(/^v/, "").split(".")[0]);
            if (nodeVersion >= 22) {
              if (typeof globalThis.WebSocket !== "undefined") {
                return { type: "native", constructor: globalThis.WebSocket };
              }
              return {
                type: "unsupported",
                error: `Node.js ${nodeVersion} detected but native WebSocket not found.`,
                workaround: "Provide a WebSocket implementation via the transport option."
              };
            }
            return {
              type: "unsupported",
              error: `Node.js ${nodeVersion} detected without native WebSocket support.`,
              workaround: 'For Node.js < 22, install "ws" package and provide it via the transport option:\nimport ws from "ws"\nnew RealtimeClient(url, { transport: ws })'
            };
          }
        }
        return {
          type: "unsupported",
          error: "Unknown JavaScript runtime without WebSocket support.",
          workaround: "Ensure you're running in a supported environment (browser, Node.js, Deno) or provide a custom WebSocket implementation."
        };
      }
      /**
       * Returns the best available WebSocket constructor for the current runtime.
       *
       * @category Realtime
       *
       * @example Example with error handling
       * ```ts
       * try {
       *   const WS = WebSocketFactory.getWebSocketConstructor()
       *   const socket = new WS('wss://example.com/socket')
       * } catch (error) {
       *   console.error('WebSocket not available in this environment.', error)
       * }
       * ```
       */
      static getWebSocketConstructor() {
        const env2 = this.detectEnvironment();
        if (env2.constructor) {
          return env2.constructor;
        }
        let errorMessage = env2.error || "WebSocket not supported in this environment.";
        if (env2.workaround) {
          errorMessage += `

Suggested solution: ${env2.workaround}`;
        }
        throw new Error(errorMessage);
      }
      /**
       * Detects whether the runtime can establish WebSocket connections.
       *
       * @category Realtime
       *
       * @example Example in a Node.js script
       * ```ts
       * if (!WebSocketFactory.isWebSocketSupported()) {
       *   console.error('WebSockets are required for this script.')
       *   process.exitCode = 1
       * }
       * ```
       */
      static isWebSocketSupported() {
        try {
          const env2 = this.detectEnvironment();
          return env2.type === "native" || env2.type === "ws";
        } catch (_a) {
          return false;
        }
      }
    };
    exports2.WebSocketFactory = WebSocketFactory;
    exports2.default = WebSocketFactory;
  }
});

// design/node_modules/@supabase/realtime-js/dist/main/lib/version.js
var require_version = __commonJS({
  "design/node_modules/@supabase/realtime-js/dist/main/lib/version.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.version = void 0;
    exports2.version = "2.104.1";
  }
});

// design/node_modules/@supabase/realtime-js/dist/main/lib/constants.js
var require_constants = __commonJS({
  "design/node_modules/@supabase/realtime-js/dist/main/lib/constants.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.CONNECTION_STATE = exports2.TRANSPORTS = exports2.CHANNEL_EVENTS = exports2.CHANNEL_STATES = exports2.SOCKET_STATES = exports2.MAX_PUSH_BUFFER_SIZE = exports2.WS_CLOSE_NORMAL = exports2.DEFAULT_TIMEOUT = exports2.VERSION = exports2.DEFAULT_VSN = exports2.VSN_2_0_0 = exports2.VSN_1_0_0 = exports2.DEFAULT_VERSION = void 0;
    var version_1 = require_version();
    exports2.DEFAULT_VERSION = `realtime-js/${version_1.version}`;
    exports2.VSN_1_0_0 = "1.0.0";
    exports2.VSN_2_0_0 = "2.0.0";
    exports2.DEFAULT_VSN = exports2.VSN_2_0_0;
    exports2.VERSION = version_1.version;
    exports2.DEFAULT_TIMEOUT = 1e4;
    exports2.WS_CLOSE_NORMAL = 1e3;
    exports2.MAX_PUSH_BUFFER_SIZE = 100;
    exports2.SOCKET_STATES = {
      connecting: 0,
      open: 1,
      closing: 2,
      closed: 3
    };
    exports2.CHANNEL_STATES = {
      closed: "closed",
      errored: "errored",
      joined: "joined",
      joining: "joining",
      leaving: "leaving"
    };
    exports2.CHANNEL_EVENTS = {
      close: "phx_close",
      error: "phx_error",
      join: "phx_join",
      reply: "phx_reply",
      leave: "phx_leave",
      access_token: "access_token"
    };
    exports2.TRANSPORTS = {
      websocket: "websocket"
    };
    exports2.CONNECTION_STATE = {
      connecting: "connecting",
      open: "open",
      closing: "closing",
      closed: "closed"
    };
  }
});

// design/node_modules/@supabase/realtime-js/dist/main/lib/serializer.js
var require_serializer = __commonJS({
  "design/node_modules/@supabase/realtime-js/dist/main/lib/serializer.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    var Serializer = class {
      constructor(allowedMetadataKeys) {
        this.HEADER_LENGTH = 1;
        this.USER_BROADCAST_PUSH_META_LENGTH = 6;
        this.KINDS = { userBroadcastPush: 3, userBroadcast: 4 };
        this.BINARY_ENCODING = 0;
        this.JSON_ENCODING = 1;
        this.BROADCAST_EVENT = "broadcast";
        this.allowedMetadataKeys = [];
        this.allowedMetadataKeys = allowedMetadataKeys !== null && allowedMetadataKeys !== void 0 ? allowedMetadataKeys : [];
      }
      encode(msg, callback) {
        if (msg.event === this.BROADCAST_EVENT && !(msg.payload instanceof ArrayBuffer) && typeof msg.payload.event === "string") {
          return callback(this._binaryEncodeUserBroadcastPush(msg));
        }
        let payload = [msg.join_ref, msg.ref, msg.topic, msg.event, msg.payload];
        return callback(JSON.stringify(payload));
      }
      _binaryEncodeUserBroadcastPush(message) {
        var _a;
        if (this._isArrayBuffer((_a = message.payload) === null || _a === void 0 ? void 0 : _a.payload)) {
          return this._encodeBinaryUserBroadcastPush(message);
        } else {
          return this._encodeJsonUserBroadcastPush(message);
        }
      }
      _encodeBinaryUserBroadcastPush(message) {
        var _a, _b;
        const userPayload = (_b = (_a = message.payload) === null || _a === void 0 ? void 0 : _a.payload) !== null && _b !== void 0 ? _b : new ArrayBuffer(0);
        return this._encodeUserBroadcastPush(message, this.BINARY_ENCODING, userPayload);
      }
      _encodeJsonUserBroadcastPush(message) {
        var _a, _b;
        const userPayload = (_b = (_a = message.payload) === null || _a === void 0 ? void 0 : _a.payload) !== null && _b !== void 0 ? _b : {};
        const encoder = new TextEncoder();
        const encodedUserPayload = encoder.encode(JSON.stringify(userPayload)).buffer;
        return this._encodeUserBroadcastPush(message, this.JSON_ENCODING, encodedUserPayload);
      }
      _encodeUserBroadcastPush(message, encodingType, encodedPayload) {
        var _a, _b;
        const topic = message.topic;
        const ref = (_a = message.ref) !== null && _a !== void 0 ? _a : "";
        const joinRef = (_b = message.join_ref) !== null && _b !== void 0 ? _b : "";
        const userEvent = message.payload.event;
        const rest = this.allowedMetadataKeys ? this._pick(message.payload, this.allowedMetadataKeys) : {};
        const metadata = Object.keys(rest).length === 0 ? "" : JSON.stringify(rest);
        if (joinRef.length > 255) {
          throw new Error(`joinRef length ${joinRef.length} exceeds maximum of 255`);
        }
        if (ref.length > 255) {
          throw new Error(`ref length ${ref.length} exceeds maximum of 255`);
        }
        if (topic.length > 255) {
          throw new Error(`topic length ${topic.length} exceeds maximum of 255`);
        }
        if (userEvent.length > 255) {
          throw new Error(`userEvent length ${userEvent.length} exceeds maximum of 255`);
        }
        if (metadata.length > 255) {
          throw new Error(`metadata length ${metadata.length} exceeds maximum of 255`);
        }
        const metaLength = this.USER_BROADCAST_PUSH_META_LENGTH + joinRef.length + ref.length + topic.length + userEvent.length + metadata.length;
        const header = new ArrayBuffer(this.HEADER_LENGTH + metaLength);
        let view = new DataView(header);
        let offset = 0;
        view.setUint8(offset++, this.KINDS.userBroadcastPush);
        view.setUint8(offset++, joinRef.length);
        view.setUint8(offset++, ref.length);
        view.setUint8(offset++, topic.length);
        view.setUint8(offset++, userEvent.length);
        view.setUint8(offset++, metadata.length);
        view.setUint8(offset++, encodingType);
        Array.from(joinRef, (char) => view.setUint8(offset++, char.charCodeAt(0)));
        Array.from(ref, (char) => view.setUint8(offset++, char.charCodeAt(0)));
        Array.from(topic, (char) => view.setUint8(offset++, char.charCodeAt(0)));
        Array.from(userEvent, (char) => view.setUint8(offset++, char.charCodeAt(0)));
        Array.from(metadata, (char) => view.setUint8(offset++, char.charCodeAt(0)));
        var combined = new Uint8Array(header.byteLength + encodedPayload.byteLength);
        combined.set(new Uint8Array(header), 0);
        combined.set(new Uint8Array(encodedPayload), header.byteLength);
        return combined.buffer;
      }
      decode(rawPayload, callback) {
        if (this._isArrayBuffer(rawPayload)) {
          let result = this._binaryDecode(rawPayload);
          return callback(result);
        }
        if (typeof rawPayload === "string") {
          const jsonPayload = JSON.parse(rawPayload);
          const [join_ref, ref, topic, event, payload] = jsonPayload;
          return callback({ join_ref, ref, topic, event, payload });
        }
        return callback({});
      }
      _binaryDecode(buffer) {
        const view = new DataView(buffer);
        const kind = view.getUint8(0);
        const decoder = new TextDecoder();
        switch (kind) {
          case this.KINDS.userBroadcast:
            return this._decodeUserBroadcast(buffer, view, decoder);
        }
      }
      _decodeUserBroadcast(buffer, view, decoder) {
        const topicSize = view.getUint8(1);
        const userEventSize = view.getUint8(2);
        const metadataSize = view.getUint8(3);
        const payloadEncoding = view.getUint8(4);
        let offset = this.HEADER_LENGTH + 4;
        const topic = decoder.decode(buffer.slice(offset, offset + topicSize));
        offset = offset + topicSize;
        const userEvent = decoder.decode(buffer.slice(offset, offset + userEventSize));
        offset = offset + userEventSize;
        const metadata = decoder.decode(buffer.slice(offset, offset + metadataSize));
        offset = offset + metadataSize;
        const payload = buffer.slice(offset, buffer.byteLength);
        const parsedPayload = payloadEncoding === this.JSON_ENCODING ? JSON.parse(decoder.decode(payload)) : payload;
        const data = {
          type: this.BROADCAST_EVENT,
          event: userEvent,
          payload: parsedPayload
        };
        if (metadataSize > 0) {
          data["meta"] = JSON.parse(metadata);
        }
        return { join_ref: null, ref: null, topic, event: this.BROADCAST_EVENT, payload: data };
      }
      _isArrayBuffer(buffer) {
        var _a;
        return buffer instanceof ArrayBuffer || ((_a = buffer === null || buffer === void 0 ? void 0 : buffer.constructor) === null || _a === void 0 ? void 0 : _a.name) === "ArrayBuffer";
      }
      _pick(obj, keys) {
        if (!obj || typeof obj !== "object") {
          return {};
        }
        return Object.fromEntries(Object.entries(obj).filter(([key]) => keys.includes(key)));
      }
    };
    exports2.default = Serializer;
  }
});

// design/node_modules/@supabase/realtime-js/dist/main/lib/transformers.js
var require_transformers = __commonJS({
  "design/node_modules/@supabase/realtime-js/dist/main/lib/transformers.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.httpEndpointURL = exports2.toTimestampString = exports2.toArray = exports2.toJson = exports2.toNumber = exports2.toBoolean = exports2.convertCell = exports2.convertColumn = exports2.convertChangeData = exports2.PostgresTypes = void 0;
    var PostgresTypes;
    (function(PostgresTypes2) {
      PostgresTypes2["abstime"] = "abstime";
      PostgresTypes2["bool"] = "bool";
      PostgresTypes2["date"] = "date";
      PostgresTypes2["daterange"] = "daterange";
      PostgresTypes2["float4"] = "float4";
      PostgresTypes2["float8"] = "float8";
      PostgresTypes2["int2"] = "int2";
      PostgresTypes2["int4"] = "int4";
      PostgresTypes2["int4range"] = "int4range";
      PostgresTypes2["int8"] = "int8";
      PostgresTypes2["int8range"] = "int8range";
      PostgresTypes2["json"] = "json";
      PostgresTypes2["jsonb"] = "jsonb";
      PostgresTypes2["money"] = "money";
      PostgresTypes2["numeric"] = "numeric";
      PostgresTypes2["oid"] = "oid";
      PostgresTypes2["reltime"] = "reltime";
      PostgresTypes2["text"] = "text";
      PostgresTypes2["time"] = "time";
      PostgresTypes2["timestamp"] = "timestamp";
      PostgresTypes2["timestamptz"] = "timestamptz";
      PostgresTypes2["timetz"] = "timetz";
      PostgresTypes2["tsrange"] = "tsrange";
      PostgresTypes2["tstzrange"] = "tstzrange";
    })(PostgresTypes || (exports2.PostgresTypes = PostgresTypes = {}));
    var convertChangeData = (columns, record, options = {}) => {
      var _a;
      const skipTypes = (_a = options.skipTypes) !== null && _a !== void 0 ? _a : [];
      if (!record) {
        return {};
      }
      return Object.keys(record).reduce((acc, rec_key) => {
        acc[rec_key] = (0, exports2.convertColumn)(rec_key, columns, record, skipTypes);
        return acc;
      }, {});
    };
    exports2.convertChangeData = convertChangeData;
    var convertColumn = (columnName, columns, record, skipTypes) => {
      const column = columns.find((x) => x.name === columnName);
      const colType = column === null || column === void 0 ? void 0 : column.type;
      const value = record[columnName];
      if (colType && !skipTypes.includes(colType)) {
        return (0, exports2.convertCell)(colType, value);
      }
      return noop(value);
    };
    exports2.convertColumn = convertColumn;
    var convertCell = (type, value) => {
      if (type.charAt(0) === "_") {
        const dataType = type.slice(1, type.length);
        return (0, exports2.toArray)(value, dataType);
      }
      switch (type) {
        case PostgresTypes.bool:
          return (0, exports2.toBoolean)(value);
        case PostgresTypes.float4:
        case PostgresTypes.float8:
        case PostgresTypes.int2:
        case PostgresTypes.int4:
        case PostgresTypes.int8:
        case PostgresTypes.numeric:
        case PostgresTypes.oid:
          return (0, exports2.toNumber)(value);
        case PostgresTypes.json:
        case PostgresTypes.jsonb:
          return (0, exports2.toJson)(value);
        case PostgresTypes.timestamp:
          return (0, exports2.toTimestampString)(value);
        // Format to be consistent with PostgREST
        case PostgresTypes.abstime:
        // To allow users to cast it based on Timezone
        case PostgresTypes.date:
        // To allow users to cast it based on Timezone
        case PostgresTypes.daterange:
        case PostgresTypes.int4range:
        case PostgresTypes.int8range:
        case PostgresTypes.money:
        case PostgresTypes.reltime:
        // To allow users to cast it based on Timezone
        case PostgresTypes.text:
        case PostgresTypes.time:
        // To allow users to cast it based on Timezone
        case PostgresTypes.timestamptz:
        // To allow users to cast it based on Timezone
        case PostgresTypes.timetz:
        // To allow users to cast it based on Timezone
        case PostgresTypes.tsrange:
        case PostgresTypes.tstzrange:
          return noop(value);
        default:
          return noop(value);
      }
    };
    exports2.convertCell = convertCell;
    var noop = (value) => {
      return value;
    };
    var toBoolean = (value) => {
      switch (value) {
        case "t":
          return true;
        case "f":
          return false;
        default:
          return value;
      }
    };
    exports2.toBoolean = toBoolean;
    var toNumber = (value) => {
      if (typeof value === "string") {
        const parsedValue = parseFloat(value);
        if (!Number.isNaN(parsedValue)) {
          return parsedValue;
        }
      }
      return value;
    };
    exports2.toNumber = toNumber;
    var toJson = (value) => {
      if (typeof value === "string") {
        try {
          return JSON.parse(value);
        } catch (_a) {
          return value;
        }
      }
      return value;
    };
    exports2.toJson = toJson;
    var toArray = (value, type) => {
      if (typeof value !== "string") {
        return value;
      }
      const lastIdx = value.length - 1;
      const closeBrace = value[lastIdx];
      const openBrace = value[0];
      if (openBrace === "{" && closeBrace === "}") {
        let arr;
        const valTrim = value.slice(1, lastIdx);
        try {
          arr = JSON.parse("[" + valTrim + "]");
        } catch (_) {
          arr = valTrim ? valTrim.split(",") : [];
        }
        return arr.map((val) => (0, exports2.convertCell)(type, val));
      }
      return value;
    };
    exports2.toArray = toArray;
    var toTimestampString = (value) => {
      if (typeof value === "string") {
        return value.replace(" ", "T");
      }
      return value;
    };
    exports2.toTimestampString = toTimestampString;
    var httpEndpointURL = (socketUrl) => {
      const wsUrl = new URL(socketUrl);
      wsUrl.protocol = wsUrl.protocol.replace(/^ws/i, "http");
      wsUrl.pathname = wsUrl.pathname.replace(/\/+$/, "").replace(/\/socket\/websocket$/i, "").replace(/\/socket$/i, "").replace(/\/websocket$/i, "");
      if (wsUrl.pathname === "" || wsUrl.pathname === "/") {
        wsUrl.pathname = "/api/broadcast";
      } else {
        wsUrl.pathname = wsUrl.pathname + "/api/broadcast";
      }
      return wsUrl.href;
    };
    exports2.httpEndpointURL = httpEndpointURL;
  }
});

// design/node_modules/@supabase/phoenix/priv/static/phoenix.cjs.js
var require_phoenix_cjs = __commonJS({
  "design/node_modules/@supabase/phoenix/priv/static/phoenix.cjs.js"(exports2, module2) {
    "use strict";
    var __defProp2 = Object.defineProperty;
    var __getOwnPropDesc2 = Object.getOwnPropertyDescriptor;
    var __getOwnPropNames2 = Object.getOwnPropertyNames;
    var __hasOwnProp2 = Object.prototype.hasOwnProperty;
    var __export2 = (target, all) => {
      for (var name in all)
        __defProp2(target, name, { get: all[name], enumerable: true });
    };
    var __copyProps2 = (to, from, except, desc) => {
      if (from && typeof from === "object" || typeof from === "function") {
        for (let key of __getOwnPropNames2(from))
          if (!__hasOwnProp2.call(to, key) && key !== except)
            __defProp2(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc2(from, key)) || desc.enumerable });
      }
      return to;
    };
    var __toCommonJS2 = (mod) => __copyProps2(__defProp2({}, "__esModule", { value: true }), mod);
    var phoenix_exports = {};
    __export2(phoenix_exports, {
      Channel: () => Channel,
      LongPoll: () => LongPoll,
      Presence: () => Presence,
      Push: () => Push,
      Serializer: () => serializer_default,
      Socket: () => Socket,
      Timer: () => Timer
    });
    module2.exports = __toCommonJS2(phoenix_exports);
    var closure = (value) => {
      if (typeof value === "function") {
        return (
          /** @type {() => T} */
          value
        );
      } else {
        let closure2 = function() {
          return value;
        };
        return closure2;
      }
    };
    var globalSelf = typeof self !== "undefined" ? self : null;
    var phxWindow = typeof window !== "undefined" ? window : null;
    var global2 = globalSelf || phxWindow || globalThis;
    var DEFAULT_VSN = "2.0.0";
    var DEFAULT_TIMEOUT = 1e4;
    var WS_CLOSE_NORMAL = 1e3;
    var SOCKET_STATES = (
      /** @type {const} */
      { connecting: 0, open: 1, closing: 2, closed: 3 }
    );
    var CHANNEL_STATES = (
      /** @type {const} */
      {
        closed: "closed",
        errored: "errored",
        joined: "joined",
        joining: "joining",
        leaving: "leaving"
      }
    );
    var CHANNEL_EVENTS = (
      /** @type {const} */
      {
        close: "phx_close",
        error: "phx_error",
        join: "phx_join",
        reply: "phx_reply",
        leave: "phx_leave"
      }
    );
    var TRANSPORTS = (
      /** @type {const} */
      {
        longpoll: "longpoll",
        websocket: "websocket"
      }
    );
    var XHR_STATES = (
      /** @type {const} */
      {
        complete: 4
      }
    );
    var AUTH_TOKEN_PREFIX = "base64url.bearer.phx.";
    var Push = class {
      /**
       * Initializes the Push
       * @param {Channel} channel - The Channel
       * @param {ChannelEvent} event - The event, for example `"phx_join"`
       * @param {() => Record<string, unknown>} payload - The payload, for example `{user_id: 123}`
       * @param {number} timeout - The push timeout in milliseconds
       */
      constructor(channel, event, payload, timeout) {
        this.channel = channel;
        this.event = event;
        this.payload = payload || function() {
          return {};
        };
        this.receivedResp = null;
        this.timeout = timeout;
        this.timeoutTimer = null;
        this.recHooks = [];
        this.sent = false;
        this.ref = void 0;
      }
      /**
       *
       * @param {number} timeout
       */
      resend(timeout) {
        this.timeout = timeout;
        this.reset();
        this.send();
      }
      /**
       *
       */
      send() {
        if (this.hasReceived("timeout")) {
          return;
        }
        this.startTimeout();
        this.sent = true;
        this.channel.socket.push({
          topic: this.channel.topic,
          event: this.event,
          payload: this.payload(),
          ref: this.ref,
          join_ref: this.channel.joinRef()
        });
      }
      /**
       *
       * @param {string} status
       * @param {(response: any) => void} callback
       */
      receive(status, callback) {
        if (this.hasReceived(status)) {
          callback(this.receivedResp.response);
        }
        this.recHooks.push({ status, callback });
        return this;
      }
      reset() {
        this.cancelRefEvent();
        this.ref = null;
        this.refEvent = null;
        this.receivedResp = null;
        this.sent = false;
      }
      destroy() {
        this.cancelRefEvent();
        this.cancelTimeout();
      }
      /**
       * @private
       */
      matchReceive({ status, response: response2, _ref }) {
        this.recHooks.filter((h) => h.status === status).forEach((h) => h.callback(response2));
      }
      /**
       * @private
       */
      cancelRefEvent() {
        if (!this.refEvent) {
          return;
        }
        this.channel.off(this.refEvent);
      }
      cancelTimeout() {
        clearTimeout(this.timeoutTimer);
        this.timeoutTimer = null;
      }
      startTimeout() {
        if (this.timeoutTimer) {
          this.cancelTimeout();
        }
        this.ref = this.channel.socket.makeRef();
        this.refEvent = this.channel.replyEventName(this.ref);
        this.channel.on(this.refEvent, (payload) => {
          this.cancelRefEvent();
          this.cancelTimeout();
          this.receivedResp = payload;
          this.matchReceive(payload);
        });
        this.timeoutTimer = setTimeout(() => {
          this.trigger("timeout", {});
        }, this.timeout);
      }
      /**
       * @private
       */
      hasReceived(status) {
        return this.receivedResp && this.receivedResp.status === status;
      }
      trigger(status, response2) {
        this.channel.trigger(this.refEvent, { status, response: response2 });
      }
    };
    var Timer = class {
      /**
      * @param {() => void} callback
      * @param {(tries: number) => number} timerCalc
      */
      constructor(callback, timerCalc) {
        this.callback = callback;
        this.timerCalc = timerCalc;
        this.timer = void 0;
        this.tries = 0;
      }
      reset() {
        this.tries = 0;
        clearTimeout(this.timer);
      }
      /**
       * Cancels any previous scheduleTimeout and schedules callback
       */
      scheduleTimeout() {
        clearTimeout(this.timer);
        this.timer = setTimeout(() => {
          this.tries = this.tries + 1;
          this.callback();
        }, this.timerCalc(this.tries + 1));
      }
    };
    var Channel = class {
      /**
       * @param {string} topic
       * @param {Params | (() => Params)} params
       * @param {Socket} socket
       */
      constructor(topic, params, socket) {
        this.state = CHANNEL_STATES.closed;
        this.topic = topic;
        this.params = closure(params || {});
        this.socket = socket;
        this.bindings = [];
        this.bindingRef = 0;
        this.timeout = this.socket.timeout;
        this.joinedOnce = false;
        this.joinPush = new Push(this, CHANNEL_EVENTS.join, this.params, this.timeout);
        this.pushBuffer = [];
        this.stateChangeRefs = [];
        this.rejoinTimer = new Timer(() => {
          if (this.socket.isConnected()) {
            this.rejoin();
          }
        }, this.socket.rejoinAfterMs);
        this.stateChangeRefs.push(this.socket.onError(() => this.rejoinTimer.reset()));
        this.stateChangeRefs.push(
          this.socket.onOpen(() => {
            this.rejoinTimer.reset();
            if (this.isErrored()) {
              this.rejoin();
            }
          })
        );
        this.joinPush.receive("ok", () => {
          this.state = CHANNEL_STATES.joined;
          this.rejoinTimer.reset();
          this.pushBuffer.forEach((pushEvent) => pushEvent.send());
          this.pushBuffer = [];
        });
        this.joinPush.receive("error", (reason) => {
          this.state = CHANNEL_STATES.errored;
          if (this.socket.hasLogger()) this.socket.log("channel", `error ${this.topic}`, reason);
          if (this.socket.isConnected()) {
            this.rejoinTimer.scheduleTimeout();
          }
        });
        this.onClose(() => {
          this.rejoinTimer.reset();
          if (this.socket.hasLogger()) this.socket.log("channel", `close ${this.topic}`);
          this.state = CHANNEL_STATES.closed;
          this.socket.remove(this);
        });
        this.onError((reason) => {
          if (this.socket.hasLogger()) this.socket.log("channel", `error ${this.topic}`, reason);
          if (this.isJoining()) {
            this.joinPush.reset();
          }
          this.state = CHANNEL_STATES.errored;
          if (this.socket.isConnected()) {
            this.rejoinTimer.scheduleTimeout();
          }
        });
        this.joinPush.receive("timeout", () => {
          if (this.socket.hasLogger()) this.socket.log("channel", `timeout ${this.topic}`, this.joinPush.timeout);
          let leavePush = new Push(this, CHANNEL_EVENTS.leave, closure({}), this.timeout);
          leavePush.send();
          this.state = CHANNEL_STATES.errored;
          this.joinPush.reset();
          if (this.socket.isConnected()) {
            this.rejoinTimer.scheduleTimeout();
          }
        });
        this.on(CHANNEL_EVENTS.reply, (payload, ref) => {
          this.trigger(this.replyEventName(ref), payload);
        });
      }
      /**
       * Join the channel
       * @param {number} timeout
       * @returns {Push}
       */
      join(timeout = this.timeout) {
        if (this.joinedOnce) {
          throw new Error("tried to join multiple times. 'join' can only be called a single time per channel instance");
        } else {
          this.timeout = timeout;
          this.joinedOnce = true;
          this.rejoin();
          return this.joinPush;
        }
      }
      /**
       * Teardown the channel.
       *
       * Destroys and stops related timers.
       */
      teardown() {
        this.pushBuffer.forEach((push) => push.destroy());
        this.pushBuffer = [];
        this.rejoinTimer.reset();
        this.joinPush.destroy();
        this.state = CHANNEL_STATES.closed;
        this.bindings = [];
      }
      /**
       * Hook into channel close
       * @param {ChannelBindingCallback} callback
       */
      onClose(callback) {
        this.on(CHANNEL_EVENTS.close, callback);
      }
      /**
       * Hook into channel errors
       * @param {ChannelOnErrorCallback} callback
       * @return {number}
       */
      onError(callback) {
        return this.on(CHANNEL_EVENTS.error, (reason) => callback(reason));
      }
      /**
       * Subscribes on channel events
       *
       * Subscription returns a ref counter, which can be used later to
       * unsubscribe the exact event listener
       *
       * @example
       * const ref1 = channel.on("event", do_stuff)
       * const ref2 = channel.on("event", do_other_stuff)
       * channel.off("event", ref1)
       * // Since unsubscription, do_stuff won't fire,
       * // while do_other_stuff will keep firing on the "event"
       *
       * @param {string} event
       * @param {ChannelBindingCallback} callback
       * @returns {number} ref
       */
      on(event, callback) {
        let ref = this.bindingRef++;
        this.bindings.push({ event, ref, callback });
        return ref;
      }
      /**
       * Unsubscribes off of channel events
       *
       * Use the ref returned from a channel.on() to unsubscribe one
       * handler, or pass nothing for the ref to unsubscribe all
       * handlers for the given event.
       *
       * @example
       * // Unsubscribe the do_stuff handler
       * const ref1 = channel.on("event", do_stuff)
       * channel.off("event", ref1)
       *
       * // Unsubscribe all handlers from event
       * channel.off("event")
       *
       * @param {string} event
       * @param {number} [ref]
       */
      off(event, ref) {
        this.bindings = this.bindings.filter((bind) => {
          return !(bind.event === event && (typeof ref === "undefined" || ref === bind.ref));
        });
      }
      /**
       * @private
       */
      canPush() {
        return this.socket.isConnected() && this.isJoined();
      }
      /**
       * Sends a message `event` to phoenix with the payload `payload`.
       * Phoenix receives this in the `handle_in(event, payload, socket)`
       * function. if phoenix replies or it times out (default 10000ms),
       * then optionally the reply can be received.
       *
       * @example
       * channel.push("event")
       *   .receive("ok", payload => console.log("phoenix replied:", payload))
       *   .receive("error", err => console.log("phoenix errored", err))
       *   .receive("timeout", () => console.log("timed out pushing"))
       * @param {string} event
       * @param {Object} payload
       * @param {number} [timeout]
       * @returns {Push}
       */
      push(event, payload, timeout = this.timeout) {
        payload = payload || {};
        if (!this.joinedOnce) {
          throw new Error(`tried to push '${event}' to '${this.topic}' before joining. Use channel.join() before pushing events`);
        }
        let pushEvent = new Push(this, event, function() {
          return payload;
        }, timeout);
        if (this.canPush()) {
          pushEvent.send();
        } else {
          pushEvent.startTimeout();
          this.pushBuffer.push(pushEvent);
        }
        return pushEvent;
      }
      /** Leaves the channel
       *
       * Unsubscribes from server events, and
       * instructs channel to terminate on server
       *
       * Triggers onClose() hooks
       *
       * To receive leave acknowledgements, use the `receive`
       * hook to bind to the server ack, ie:
       *
       * @example
       * channel.leave().receive("ok", () => alert("left!") )
       *
       * @param {number} timeout
       * @returns {Push}
       */
      leave(timeout = this.timeout) {
        this.rejoinTimer.reset();
        this.joinPush.cancelTimeout();
        this.state = CHANNEL_STATES.leaving;
        let onClose = () => {
          if (this.socket.hasLogger()) this.socket.log("channel", `leave ${this.topic}`);
          this.trigger(CHANNEL_EVENTS.close, "leave");
        };
        let leavePush = new Push(this, CHANNEL_EVENTS.leave, closure({}), timeout);
        leavePush.receive("ok", () => onClose()).receive("timeout", () => onClose());
        leavePush.send();
        if (!this.canPush()) {
          leavePush.trigger("ok", {});
        }
        return leavePush;
      }
      /**
       * Overridable message hook
       *
       * Receives all events for specialized message handling
       * before dispatching to the channel callbacks.
       *
       * Must return the payload, modified or unmodified
       * @type{ChannelOnMessage}
       */
      onMessage(_event, payload, _ref) {
        return payload;
      }
      /**
       * Overridable filter hook
       *
       * If this function returns `true`, `binding`'s callback will be called.
       *
       * @type{ChannelFilterBindings}
       */
      filterBindings(_binding, _payload, _ref) {
        return true;
      }
      isMember(topic, event, payload, joinRef) {
        if (this.topic !== topic) {
          return false;
        }
        if (joinRef && joinRef !== this.joinRef()) {
          if (this.socket.hasLogger()) this.socket.log("channel", "dropping outdated message", { topic, event, payload, joinRef });
          return false;
        } else {
          return true;
        }
      }
      joinRef() {
        return this.joinPush.ref;
      }
      /**
       * @private
       */
      rejoin(timeout = this.timeout) {
        if (this.isLeaving()) {
          return;
        }
        this.socket.leaveOpenTopic(this.topic);
        this.state = CHANNEL_STATES.joining;
        this.joinPush.resend(timeout);
      }
      /**
       * @param {string} event
       * @param {unknown} [payload]
       * @param {?string} [ref]
       * @param {?string} [joinRef]
       */
      trigger(event, payload, ref, joinRef) {
        let handledPayload = this.onMessage(event, payload, ref, joinRef);
        if (payload && !handledPayload) {
          throw new Error("channel onMessage callbacks must return the payload, modified or unmodified");
        }
        let eventBindings = this.bindings.filter((bind) => bind.event === event && this.filterBindings(bind, payload, ref));
        for (let i = 0; i < eventBindings.length; i++) {
          let bind = eventBindings[i];
          bind.callback(handledPayload, ref, joinRef || this.joinRef());
        }
      }
      /**
      * @param {string} ref
      */
      replyEventName(ref) {
        return `chan_reply_${ref}`;
      }
      isClosed() {
        return this.state === CHANNEL_STATES.closed;
      }
      isErrored() {
        return this.state === CHANNEL_STATES.errored;
      }
      isJoined() {
        return this.state === CHANNEL_STATES.joined;
      }
      isJoining() {
        return this.state === CHANNEL_STATES.joining;
      }
      isLeaving() {
        return this.state === CHANNEL_STATES.leaving;
      }
    };
    var Ajax = class {
      static request(method, endPoint, headers, body, timeout, ontimeout, callback) {
        if (global2.XDomainRequest) {
          let req = new global2.XDomainRequest();
          return this.xdomainRequest(req, method, endPoint, body, timeout, ontimeout, callback);
        } else if (global2.XMLHttpRequest) {
          let req = new global2.XMLHttpRequest();
          return this.xhrRequest(req, method, endPoint, headers, body, timeout, ontimeout, callback);
        } else if (global2.fetch && global2.AbortController) {
          return this.fetchRequest(method, endPoint, headers, body, timeout, ontimeout, callback);
        } else {
          throw new Error("No suitable XMLHttpRequest implementation found");
        }
      }
      static fetchRequest(method, endPoint, headers, body, timeout, ontimeout, callback) {
        let options = {
          method,
          headers,
          body
        };
        let controller = null;
        if (timeout) {
          controller = new AbortController();
          const _timeoutId = setTimeout(() => controller.abort(), timeout);
          options.signal = controller.signal;
        }
        global2.fetch(endPoint, options).then((response2) => response2.text()).then((data) => this.parseJSON(data)).then((data) => callback && callback(data)).catch((err) => {
          if (err.name === "AbortError" && ontimeout) {
            ontimeout();
          } else {
            callback && callback(null);
          }
        });
        return controller;
      }
      static xdomainRequest(req, method, endPoint, body, timeout, ontimeout, callback) {
        req.timeout = timeout;
        req.open(method, endPoint);
        req.onload = () => {
          let response2 = this.parseJSON(req.responseText);
          callback && callback(response2);
        };
        if (ontimeout) {
          req.ontimeout = ontimeout;
        }
        req.onprogress = () => {
        };
        req.send(body);
        return req;
      }
      static xhrRequest(req, method, endPoint, headers, body, timeout, ontimeout, callback) {
        req.open(method, endPoint, true);
        req.timeout = timeout;
        for (let [key, value] of Object.entries(headers)) {
          req.setRequestHeader(key, value);
        }
        req.onerror = () => callback && callback(null);
        req.onreadystatechange = () => {
          if (req.readyState === XHR_STATES.complete && callback) {
            let response2 = this.parseJSON(req.responseText);
            callback(response2);
          }
        };
        if (ontimeout) {
          req.ontimeout = ontimeout;
        }
        req.send(body);
        return req;
      }
      static parseJSON(resp) {
        if (!resp || resp === "") {
          return null;
        }
        try {
          return JSON.parse(resp);
        } catch {
          console && console.log("failed to parse JSON response", resp);
          return null;
        }
      }
      static serialize(obj, parentKey) {
        let queryStr = [];
        for (var key in obj) {
          if (!Object.prototype.hasOwnProperty.call(obj, key)) {
            continue;
          }
          let paramKey = parentKey ? `${parentKey}[${key}]` : key;
          let paramVal = obj[key];
          if (typeof paramVal === "object") {
            queryStr.push(this.serialize(paramVal, paramKey));
          } else {
            queryStr.push(encodeURIComponent(paramKey) + "=" + encodeURIComponent(paramVal));
          }
        }
        return queryStr.join("&");
      }
      static appendParams(url, params) {
        if (Object.keys(params).length === 0) {
          return url;
        }
        let prefix = url.match(/\?/) ? "&" : "?";
        return `${url}${prefix}${this.serialize(params)}`;
      }
    };
    var arrayBufferToBase64 = (buffer) => {
      let binary = "";
      let bytes = new Uint8Array(buffer);
      let len = bytes.byteLength;
      for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      return btoa(binary);
    };
    var LongPoll = class {
      constructor(endPoint, protocols) {
        if (protocols && protocols.length === 2 && protocols[1].startsWith(AUTH_TOKEN_PREFIX)) {
          this.authToken = atob(protocols[1].slice(AUTH_TOKEN_PREFIX.length));
        }
        this.endPoint = null;
        this.token = null;
        this.skipHeartbeat = true;
        this.reqs = /* @__PURE__ */ new Set();
        this.awaitingBatchAck = false;
        this.currentBatch = null;
        this.currentBatchTimer = null;
        this.batchBuffer = [];
        this.onopen = function() {
        };
        this.onerror = function() {
        };
        this.onmessage = function() {
        };
        this.onclose = function() {
        };
        this.pollEndpoint = this.normalizeEndpoint(endPoint);
        this.readyState = SOCKET_STATES.connecting;
        setTimeout(() => this.poll(), 0);
      }
      normalizeEndpoint(endPoint) {
        return endPoint.replace("ws://", "http://").replace("wss://", "https://").replace(new RegExp("(.*)/" + TRANSPORTS.websocket), "$1/" + TRANSPORTS.longpoll);
      }
      endpointURL() {
        return Ajax.appendParams(this.pollEndpoint, { token: this.token });
      }
      closeAndRetry(code, reason, wasClean) {
        this.close(code, reason, wasClean);
        this.readyState = SOCKET_STATES.connecting;
      }
      ontimeout() {
        this.onerror("timeout");
        this.closeAndRetry(1005, "timeout", false);
      }
      isActive() {
        return this.readyState === SOCKET_STATES.open || this.readyState === SOCKET_STATES.connecting;
      }
      poll() {
        const headers = { "Accept": "application/json" };
        if (this.authToken) {
          headers["X-Phoenix-AuthToken"] = this.authToken;
        }
        this.ajax("GET", headers, null, () => this.ontimeout(), (resp) => {
          if (resp) {
            var { status, token, messages } = resp;
            if (status === 410 && this.token !== null) {
              this.onerror(410);
              this.closeAndRetry(3410, "session_gone", false);
              return;
            }
            this.token = token;
          } else {
            status = 0;
          }
          switch (status) {
            case 200:
              messages.forEach((msg) => {
                setTimeout(() => this.onmessage({ data: msg }), 0);
              });
              this.poll();
              break;
            case 204:
              this.poll();
              break;
            case 410:
              this.readyState = SOCKET_STATES.open;
              this.onopen({});
              this.poll();
              break;
            case 403:
              this.onerror(403);
              this.close(1008, "forbidden", false);
              break;
            case 0:
            case 500:
              this.onerror(500);
              this.closeAndRetry(1011, "internal server error", 500);
              break;
            default:
              throw new Error(`unhandled poll status ${status}`);
          }
        });
      }
      // we collect all pushes within the current event loop by
      // setTimeout 0, which optimizes back-to-back procedural
      // pushes against an empty buffer
      send(body) {
        if (typeof body !== "string") {
          body = arrayBufferToBase64(body);
        }
        if (this.currentBatch) {
          this.currentBatch.push(body);
        } else if (this.awaitingBatchAck) {
          this.batchBuffer.push(body);
        } else {
          this.currentBatch = [body];
          this.currentBatchTimer = setTimeout(() => {
            this.batchSend(this.currentBatch);
            this.currentBatch = null;
          }, 0);
        }
      }
      batchSend(messages) {
        this.awaitingBatchAck = true;
        this.ajax("POST", { "Content-Type": "application/x-ndjson" }, messages.join("\n"), () => this.onerror("timeout"), (resp) => {
          this.awaitingBatchAck = false;
          if (!resp || resp.status !== 200) {
            this.onerror(resp && resp.status);
            this.closeAndRetry(1011, "internal server error", false);
          } else if (this.batchBuffer.length > 0) {
            this.batchSend(this.batchBuffer);
            this.batchBuffer = [];
          }
        });
      }
      close(code, reason, wasClean) {
        for (let req of this.reqs) {
          req.abort();
        }
        this.readyState = SOCKET_STATES.closed;
        let opts = Object.assign({ code: 1e3, reason: void 0, wasClean: true }, { code, reason, wasClean });
        this.batchBuffer = [];
        clearTimeout(this.currentBatchTimer);
        this.currentBatchTimer = null;
        if (typeof CloseEvent !== "undefined") {
          this.onclose(new CloseEvent("close", opts));
        } else {
          this.onclose(opts);
        }
      }
      ajax(method, headers, body, onCallerTimeout, callback) {
        let req;
        let ontimeout = () => {
          this.reqs.delete(req);
          onCallerTimeout();
        };
        req = Ajax.request(method, this.endpointURL(), headers, body, this.timeout, ontimeout, (resp) => {
          this.reqs.delete(req);
          if (this.isActive()) {
            callback(resp);
          }
        });
        this.reqs.add(req);
      }
    };
    var Presence = class _Presence {
      /**
       * Initializes the Presence
       * @param {Channel} channel - The Channel
       * @param {PresenceOptions} [opts] - The options, for example `{events: {state: "state", diff: "diff"}}`
       */
      constructor(channel, opts = {}) {
        let events = opts.events || /** @type {PresenceEvents} */
        { state: "presence_state", diff: "presence_diff" };
        this.state = {};
        this.pendingDiffs = [];
        this.channel = channel;
        this.joinRef = null;
        this.caller = {
          onJoin: function() {
          },
          onLeave: function() {
          },
          onSync: function() {
          }
        };
        this.channel.on(events.state, (newState) => {
          let { onJoin, onLeave, onSync } = this.caller;
          this.joinRef = this.channel.joinRef();
          this.state = _Presence.syncState(this.state, newState, onJoin, onLeave);
          this.pendingDiffs.forEach((diff) => {
            this.state = _Presence.syncDiff(this.state, diff, onJoin, onLeave);
          });
          this.pendingDiffs = [];
          onSync();
        });
        this.channel.on(events.diff, (diff) => {
          let { onJoin, onLeave, onSync } = this.caller;
          if (this.inPendingSyncState()) {
            this.pendingDiffs.push(diff);
          } else {
            this.state = _Presence.syncDiff(this.state, diff, onJoin, onLeave);
            onSync();
          }
        });
      }
      /**
       * @param {PresenceOnJoin} callback
       */
      onJoin(callback) {
        this.caller.onJoin = callback;
      }
      /**
       * @param {PresenceOnLeave} callback
       */
      onLeave(callback) {
        this.caller.onLeave = callback;
      }
      /**
       * @param {PresenceOnSync} callback
       */
      onSync(callback) {
        this.caller.onSync = callback;
      }
      /**
       * Returns the array of presences, with selected metadata.
       *
       * @template [T=PresenceState]
       * @param {((key: string, obj: PresenceState) => T)} [by]
       *
       * @returns {T[]}
       */
      list(by) {
        return _Presence.list(this.state, by);
      }
      inPendingSyncState() {
        return !this.joinRef || this.joinRef !== this.channel.joinRef();
      }
      // lower-level public static API
      /**
       * Used to sync the list of presences on the server
       * with the client's state. An optional `onJoin` and `onLeave` callback can
       * be provided to react to changes in the client's local presences across
       * disconnects and reconnects with the server.
       *
       * @param {Record<string, PresenceState>} currentState
       * @param {Record<string, PresenceState>} newState
       * @param {PresenceOnJoin} onJoin
       * @param {PresenceOnLeave} onLeave
       *
       * @returns {Record<string, PresenceState>}
       */
      static syncState(currentState, newState, onJoin, onLeave) {
        let state = this.clone(currentState);
        let joins = {};
        let leaves = {};
        this.map(state, (key, presence) => {
          if (!newState[key]) {
            leaves[key] = presence;
          }
        });
        this.map(newState, (key, newPresence) => {
          let currentPresence = state[key];
          if (currentPresence) {
            let newRefs = newPresence.metas.map((m) => m.phx_ref);
            let curRefs = currentPresence.metas.map((m) => m.phx_ref);
            let joinedMetas = newPresence.metas.filter((m) => curRefs.indexOf(m.phx_ref) < 0);
            let leftMetas = currentPresence.metas.filter((m) => newRefs.indexOf(m.phx_ref) < 0);
            if (joinedMetas.length > 0) {
              joins[key] = newPresence;
              joins[key].metas = joinedMetas;
            }
            if (leftMetas.length > 0) {
              leaves[key] = this.clone(currentPresence);
              leaves[key].metas = leftMetas;
            }
          } else {
            joins[key] = newPresence;
          }
        });
        return this.syncDiff(state, { joins, leaves }, onJoin, onLeave);
      }
      /**
       *
       * Used to sync a diff of presence join and leave
       * events from the server, as they happen. Like `syncState`, `syncDiff`
       * accepts optional `onJoin` and `onLeave` callbacks to react to a user
       * joining or leaving from a device.
       *
       * @param {Record<string, PresenceState>} state
       * @param {PresenceDiff} diff
       * @param {PresenceOnJoin} onJoin
       * @param {PresenceOnLeave} onLeave
       *
       * @returns {Record<string, PresenceState>}
       */
      static syncDiff(state, diff, onJoin, onLeave) {
        let { joins, leaves } = this.clone(diff);
        if (!onJoin) {
          onJoin = function() {
          };
        }
        if (!onLeave) {
          onLeave = function() {
          };
        }
        this.map(joins, (key, newPresence) => {
          let currentPresence = state[key];
          state[key] = this.clone(newPresence);
          if (currentPresence) {
            let joinedRefs = state[key].metas.map((m) => m.phx_ref);
            let curMetas = currentPresence.metas.filter((m) => joinedRefs.indexOf(m.phx_ref) < 0);
            state[key].metas.unshift(...curMetas);
          }
          onJoin(key, currentPresence, newPresence);
        });
        this.map(leaves, (key, leftPresence) => {
          let currentPresence = state[key];
          if (!currentPresence) {
            return;
          }
          let refsToRemove = leftPresence.metas.map((m) => m.phx_ref);
          currentPresence.metas = currentPresence.metas.filter((p) => {
            return refsToRemove.indexOf(p.phx_ref) < 0;
          });
          onLeave(key, currentPresence, leftPresence);
          if (currentPresence.metas.length === 0) {
            delete state[key];
          }
        });
        return state;
      }
      /**
       * Returns the array of presences, with selected metadata.
       *
       * @template [T=PresenceState]
       * @param {Record<string, PresenceState>} presences
       * @param {((key: string, obj: PresenceState) => T)} [chooser]
       *
       * @returns {T[]}
       */
      static list(presences, chooser) {
        if (!chooser) {
          chooser = function(key, pres) {
            return pres;
          };
        }
        return this.map(presences, (key, presence) => {
          return chooser(key, presence);
        });
      }
      // private
      /**
      * @template T
      * @param {Record<string, PresenceState>} obj
      * @param {(key: string, obj: PresenceState) => T} func
      */
      static map(obj, func) {
        return Object.getOwnPropertyNames(obj).map((key) => func(key, obj[key]));
      }
      /**
      * @template T
      * @param {T} obj
      * @returns {T}
      */
      static clone(obj) {
        return JSON.parse(JSON.stringify(obj));
      }
    };
    var serializer_default = {
      HEADER_LENGTH: 1,
      META_LENGTH: 4,
      KINDS: { push: 0, reply: 1, broadcast: 2 },
      /**
      * @template T
      * @param {Message<Record<string, any>>} msg
      * @param {(msg: ArrayBuffer | string) => T} callback
      * @returns {T}
      */
      encode(msg, callback) {
        if (msg.payload.constructor === ArrayBuffer) {
          return callback(this.binaryEncode(msg));
        } else {
          let payload = [msg.join_ref, msg.ref, msg.topic, msg.event, msg.payload];
          return callback(JSON.stringify(payload));
        }
      },
      /**
      * @template T
      * @param {ArrayBuffer | string} rawPayload
      * @param {(msg: Message<unknown>) => T} callback
      * @returns {T}
      */
      decode(rawPayload, callback) {
        if (rawPayload.constructor === ArrayBuffer) {
          return callback(this.binaryDecode(rawPayload));
        } else {
          let [join_ref, ref, topic, event, payload] = JSON.parse(rawPayload);
          return callback({ join_ref, ref, topic, event, payload });
        }
      },
      /** @private */
      binaryEncode(message) {
        let { join_ref, ref, event, topic, payload } = message;
        let metaLength = this.META_LENGTH + join_ref.length + ref.length + topic.length + event.length;
        let header = new ArrayBuffer(this.HEADER_LENGTH + metaLength);
        let view = new DataView(header);
        let offset = 0;
        view.setUint8(offset++, this.KINDS.push);
        view.setUint8(offset++, join_ref.length);
        view.setUint8(offset++, ref.length);
        view.setUint8(offset++, topic.length);
        view.setUint8(offset++, event.length);
        Array.from(join_ref, (char) => view.setUint8(offset++, char.charCodeAt(0)));
        Array.from(ref, (char) => view.setUint8(offset++, char.charCodeAt(0)));
        Array.from(topic, (char) => view.setUint8(offset++, char.charCodeAt(0)));
        Array.from(event, (char) => view.setUint8(offset++, char.charCodeAt(0)));
        var combined = new Uint8Array(header.byteLength + payload.byteLength);
        combined.set(new Uint8Array(header), 0);
        combined.set(new Uint8Array(payload), header.byteLength);
        return combined.buffer;
      },
      /**
      * @private
      */
      binaryDecode(buffer) {
        let view = new DataView(buffer);
        let kind = view.getUint8(0);
        let decoder = new TextDecoder();
        switch (kind) {
          case this.KINDS.push:
            return this.decodePush(buffer, view, decoder);
          case this.KINDS.reply:
            return this.decodeReply(buffer, view, decoder);
          case this.KINDS.broadcast:
            return this.decodeBroadcast(buffer, view, decoder);
        }
      },
      /** @private */
      decodePush(buffer, view, decoder) {
        let joinRefSize = view.getUint8(1);
        let topicSize = view.getUint8(2);
        let eventSize = view.getUint8(3);
        let offset = this.HEADER_LENGTH + this.META_LENGTH - 1;
        let joinRef = decoder.decode(buffer.slice(offset, offset + joinRefSize));
        offset = offset + joinRefSize;
        let topic = decoder.decode(buffer.slice(offset, offset + topicSize));
        offset = offset + topicSize;
        let event = decoder.decode(buffer.slice(offset, offset + eventSize));
        offset = offset + eventSize;
        let data = buffer.slice(offset, buffer.byteLength);
        return { join_ref: joinRef, ref: null, topic, event, payload: data };
      },
      /** @private */
      decodeReply(buffer, view, decoder) {
        let joinRefSize = view.getUint8(1);
        let refSize = view.getUint8(2);
        let topicSize = view.getUint8(3);
        let eventSize = view.getUint8(4);
        let offset = this.HEADER_LENGTH + this.META_LENGTH;
        let joinRef = decoder.decode(buffer.slice(offset, offset + joinRefSize));
        offset = offset + joinRefSize;
        let ref = decoder.decode(buffer.slice(offset, offset + refSize));
        offset = offset + refSize;
        let topic = decoder.decode(buffer.slice(offset, offset + topicSize));
        offset = offset + topicSize;
        let event = decoder.decode(buffer.slice(offset, offset + eventSize));
        offset = offset + eventSize;
        let data = buffer.slice(offset, buffer.byteLength);
        let payload = { status: event, response: data };
        return { join_ref: joinRef, ref, topic, event: CHANNEL_EVENTS.reply, payload };
      },
      /** @private */
      decodeBroadcast(buffer, view, decoder) {
        let topicSize = view.getUint8(1);
        let eventSize = view.getUint8(2);
        let offset = this.HEADER_LENGTH + 2;
        let topic = decoder.decode(buffer.slice(offset, offset + topicSize));
        offset = offset + topicSize;
        let event = decoder.decode(buffer.slice(offset, offset + eventSize));
        offset = offset + eventSize;
        let data = buffer.slice(offset, buffer.byteLength);
        return { join_ref: null, ref: null, topic, event, payload: data };
      }
    };
    var Socket = class {
      /** Initializes the Socket *
       *
       * For IE8 support use an ES5-shim (https://github.com/es-shims/es5-shim)
       *
       * @constructor
       * @param {string} endPoint - The string WebSocket endpoint, ie, `"ws://example.com/socket"`,
       *                                               `"wss://example.com"`
       *                                               `"/socket"` (inherited host & protocol)
       * @param {SocketOptions} [opts] - Optional configuration
       */
      constructor(endPoint, opts = {}) {
        this.stateChangeCallbacks = { open: [], close: [], error: [], message: [] };
        this.channels = [];
        this.sendBuffer = [];
        this.ref = 0;
        this.fallbackRef = null;
        this.timeout = opts.timeout || DEFAULT_TIMEOUT;
        this.transport = opts.transport || global2.WebSocket || LongPoll;
        this.conn = void 0;
        this.primaryPassedHealthCheck = false;
        this.longPollFallbackMs = opts.longPollFallbackMs;
        this.fallbackTimer = null;
        this.sessionStore = opts.sessionStorage || global2 && global2.sessionStorage;
        this.establishedConnections = 0;
        this.defaultEncoder = serializer_default.encode.bind(serializer_default);
        this.defaultDecoder = serializer_default.decode.bind(serializer_default);
        this.closeWasClean = true;
        this.disconnecting = false;
        this.binaryType = opts.binaryType || "arraybuffer";
        this.connectClock = 1;
        this.pageHidden = false;
        this.encode = void 0;
        this.decode = void 0;
        if (this.transport !== LongPoll) {
          this.encode = opts.encode || this.defaultEncoder;
          this.decode = opts.decode || this.defaultDecoder;
        } else {
          this.encode = this.defaultEncoder;
          this.decode = this.defaultDecoder;
        }
        let awaitingConnectionOnPageShow = null;
        if (phxWindow && phxWindow.addEventListener) {
          phxWindow.addEventListener("pagehide", (_e) => {
            if (this.conn) {
              this.disconnect();
              awaitingConnectionOnPageShow = this.connectClock;
            }
          });
          phxWindow.addEventListener("pageshow", (_e) => {
            if (awaitingConnectionOnPageShow === this.connectClock) {
              awaitingConnectionOnPageShow = null;
              this.connect();
            }
          });
          phxWindow.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "hidden") {
              this.pageHidden = true;
            } else {
              this.pageHidden = false;
              if (!this.isConnected() && !this.closeWasClean) {
                this.teardown(() => this.connect());
              }
            }
          });
        }
        this.heartbeatIntervalMs = opts.heartbeatIntervalMs || 3e4;
        this.autoSendHeartbeat = opts.autoSendHeartbeat ?? true;
        this.heartbeatCallback = opts.heartbeatCallback ?? (() => {
        });
        this.rejoinAfterMs = (tries) => {
          if (opts.rejoinAfterMs) {
            return opts.rejoinAfterMs(tries);
          } else {
            return [1e3, 2e3, 5e3][tries - 1] || 1e4;
          }
        };
        this.reconnectAfterMs = (tries) => {
          if (opts.reconnectAfterMs) {
            return opts.reconnectAfterMs(tries);
          } else {
            return [10, 50, 100, 150, 200, 250, 500, 1e3, 2e3][tries - 1] || 5e3;
          }
        };
        this.logger = opts.logger || null;
        if (!this.logger && opts.debug) {
          this.logger = (kind, msg, data) => {
            console.log(`${kind}: ${msg}`, data);
          };
        }
        this.longpollerTimeout = opts.longpollerTimeout || 2e4;
        this.params = closure(opts.params || {});
        this.endPoint = `${endPoint}/${TRANSPORTS.websocket}`;
        this.vsn = opts.vsn || DEFAULT_VSN;
        this.heartbeatTimeoutTimer = null;
        this.heartbeatTimer = null;
        this.heartbeatSentAt = null;
        this.pendingHeartbeatRef = null;
        this.reconnectTimer = new Timer(() => {
          if (this.pageHidden) {
            this.log("Not reconnecting as page is hidden!");
            this.teardown();
            return;
          }
          this.teardown(async () => {
            if (opts.beforeReconnect) await opts.beforeReconnect();
            this.connect();
          });
        }, this.reconnectAfterMs);
        this.authToken = opts.authToken;
      }
      /**
       * Returns the LongPoll transport reference
       */
      getLongPollTransport() {
        return LongPoll;
      }
      /**
       * Disconnects and replaces the active transport
       *
       * @param {SocketTransport} newTransport - The new transport class to instantiate
       *
       */
      replaceTransport(newTransport) {
        this.connectClock++;
        this.closeWasClean = true;
        clearTimeout(this.fallbackTimer);
        this.reconnectTimer.reset();
        if (this.conn) {
          this.conn.close();
          this.conn = null;
        }
        this.transport = newTransport;
      }
      /**
       * Returns the socket protocol
       *
       * @returns {"wss" | "ws"}
       */
      protocol() {
        return location.protocol.match(/^https/) ? "wss" : "ws";
      }
      /**
       * The fully qualified socket url
       *
       * @returns {string}
       */
      endPointURL() {
        let uri = Ajax.appendParams(
          Ajax.appendParams(this.endPoint, this.params()),
          { vsn: this.vsn }
        );
        if (uri.charAt(0) !== "/") {
          return uri;
        }
        if (uri.charAt(1) === "/") {
          return `${this.protocol()}:${uri}`;
        }
        return `${this.protocol()}://${location.host}${uri}`;
      }
      /**
       * Disconnects the socket
       *
       * See https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent#Status_codes for valid status codes.
       *
       * @param {() => void} [callback] - Optional callback which is called after socket is disconnected.
       * @param {number} [code] - A status code for disconnection (Optional).
       * @param {string} [reason] - A textual description of the reason to disconnect. (Optional)
       */
      disconnect(callback, code, reason) {
        this.connectClock++;
        this.disconnecting = true;
        this.closeWasClean = true;
        clearTimeout(this.fallbackTimer);
        this.reconnectTimer.reset();
        this.teardown(() => {
          this.disconnecting = false;
          callback && callback();
        }, code, reason);
      }
      /**
       * @param {Params} [params] - [DEPRECATED] The params to send when connecting, for example `{user_id: userToken}`
       *
       * Passing params to connect is deprecated; pass them in the Socket constructor instead:
       * `new Socket("/socket", {params: {user_id: userToken}})`.
       */
      connect(params) {
        if (params) {
          console && console.log("passing params to connect is deprecated. Instead pass :params to the Socket constructor");
          this.params = closure(params);
        }
        if (this.conn && !this.disconnecting) {
          return;
        }
        if (this.longPollFallbackMs && this.transport !== LongPoll) {
          this.connectWithFallback(LongPoll, this.longPollFallbackMs);
        } else {
          this.transportConnect();
        }
      }
      /**
       * Logs the message. Override `this.logger` for specialized logging. noops by default
       * @param {string} kind
       * @param {string} msg
       * @param {Object} data
       */
      log(kind, msg, data) {
        this.logger && this.logger(kind, msg, data);
      }
      /**
       * Returns true if a logger has been set on this socket.
       */
      hasLogger() {
        return this.logger !== null;
      }
      /**
       * Registers callbacks for connection open events
       *
       * @example socket.onOpen(function(){ console.info("the socket was opened") })
       *
       * @param {SocketOnOpen} callback
       */
      onOpen(callback) {
        let ref = this.makeRef();
        this.stateChangeCallbacks.open.push([ref, callback]);
        return ref;
      }
      /**
       * Registers callbacks for connection close events
       * @param {SocketOnClose} callback
       * @returns {string}
       */
      onClose(callback) {
        let ref = this.makeRef();
        this.stateChangeCallbacks.close.push([ref, callback]);
        return ref;
      }
      /**
       * Registers callbacks for connection error events
       *
       * @example socket.onError(function(error){ alert("An error occurred") })
       *
       * @param {SocketOnError} callback
       * @returns {string}
       */
      onError(callback) {
        let ref = this.makeRef();
        this.stateChangeCallbacks.error.push([ref, callback]);
        return ref;
      }
      /**
       * Registers callbacks for connection message events
       * @param {SocketOnMessage} callback
       * @returns {string}
       */
      onMessage(callback) {
        let ref = this.makeRef();
        this.stateChangeCallbacks.message.push([ref, callback]);
        return ref;
      }
      /**
       * Sets a callback that receives lifecycle events for internal heartbeat messages.
       * Useful for instrumenting connection health (e.g. sent/ok/timeout/disconnected).
       * @param {HeartbeatCallback} callback
       */
      onHeartbeat(callback) {
        this.heartbeatCallback = callback;
      }
      /**
       * Pings the server and invokes the callback with the RTT in milliseconds
       * @param {(timeDelta: number) => void} callback
       *
       * Returns true if the ping was pushed or false if unable to be pushed.
       */
      ping(callback) {
        if (!this.isConnected()) {
          return false;
        }
        let ref = this.makeRef();
        let startTime = Date.now();
        this.push({ topic: "phoenix", event: "heartbeat", payload: {}, ref });
        let onMsgRef = this.onMessage((msg) => {
          if (msg.ref === ref) {
            this.off([onMsgRef]);
            callback(Date.now() - startTime);
          }
        });
        return true;
      }
      /**
       * @private
       *
       * @param {Function}
       */
      transportName(transport) {
        switch (transport) {
          case LongPoll:
            return "LongPoll";
          default:
            return transport.name;
        }
      }
      /**
       * @private
       */
      transportConnect() {
        this.connectClock++;
        this.closeWasClean = false;
        let protocols = void 0;
        if (this.authToken) {
          protocols = ["phoenix", `${AUTH_TOKEN_PREFIX}${btoa(this.authToken).replace(/=/g, "")}`];
        }
        this.conn = new this.transport(this.endPointURL(), protocols);
        this.conn.binaryType = this.binaryType;
        this.conn.timeout = this.longpollerTimeout;
        this.conn.onopen = () => this.onConnOpen();
        this.conn.onerror = (error) => this.onConnError(error);
        this.conn.onmessage = (event) => this.onConnMessage(event);
        this.conn.onclose = (event) => this.onConnClose(event);
      }
      getSession(key) {
        return this.sessionStore && this.sessionStore.getItem(key);
      }
      storeSession(key, val) {
        this.sessionStore && this.sessionStore.setItem(key, val);
      }
      connectWithFallback(fallbackTransport, fallbackThreshold = 2500) {
        clearTimeout(this.fallbackTimer);
        let established = false;
        let primaryTransport = true;
        let openRef, errorRef;
        let fallbackTransportName = this.transportName(fallbackTransport);
        let fallback = (reason) => {
          this.log("transport", `falling back to ${fallbackTransportName}...`, reason);
          this.off([openRef, errorRef]);
          primaryTransport = false;
          this.replaceTransport(fallbackTransport);
          this.transportConnect();
        };
        if (this.getSession(`phx:fallback:${fallbackTransportName}`)) {
          return fallback("memorized");
        }
        this.fallbackTimer = setTimeout(fallback, fallbackThreshold);
        errorRef = this.onError((reason) => {
          this.log("transport", "error", reason);
          if (primaryTransport && !established) {
            clearTimeout(this.fallbackTimer);
            fallback(reason);
          }
        });
        if (this.fallbackRef) {
          this.off([this.fallbackRef]);
        }
        this.fallbackRef = this.onOpen(() => {
          established = true;
          if (!primaryTransport) {
            let fallbackTransportName2 = this.transportName(fallbackTransport);
            if (!this.primaryPassedHealthCheck) {
              this.storeSession(`phx:fallback:${fallbackTransportName2}`, "true");
            }
            return this.log("transport", `established ${fallbackTransportName2} fallback`);
          }
          clearTimeout(this.fallbackTimer);
          this.fallbackTimer = setTimeout(fallback, fallbackThreshold);
          this.ping((rtt) => {
            this.log("transport", "connected to primary after", rtt);
            this.primaryPassedHealthCheck = true;
            clearTimeout(this.fallbackTimer);
          });
        });
        this.transportConnect();
      }
      clearHeartbeats() {
        clearTimeout(this.heartbeatTimer);
        clearTimeout(this.heartbeatTimeoutTimer);
      }
      onConnOpen() {
        if (this.hasLogger()) this.log("transport", `connected to ${this.endPointURL()}`);
        this.closeWasClean = false;
        this.disconnecting = false;
        this.establishedConnections++;
        this.flushSendBuffer();
        this.reconnectTimer.reset();
        if (this.autoSendHeartbeat) {
          this.resetHeartbeat();
        }
        this.triggerStateCallbacks("open");
      }
      /**
       * @private
       */
      heartbeatTimeout() {
        if (this.pendingHeartbeatRef) {
          this.pendingHeartbeatRef = null;
          this.heartbeatSentAt = null;
          if (this.hasLogger()) {
            this.log("transport", "heartbeat timeout. Attempting to re-establish connection");
          }
          try {
            this.heartbeatCallback("timeout");
          } catch (e) {
            this.log("error", "error in heartbeat callback", e);
          }
          this.triggerChanError();
          this.closeWasClean = false;
          this.teardown(() => this.reconnectTimer.scheduleTimeout(), WS_CLOSE_NORMAL, "heartbeat timeout");
        }
      }
      resetHeartbeat() {
        if (this.conn && this.conn.skipHeartbeat) {
          return;
        }
        this.pendingHeartbeatRef = null;
        this.clearHeartbeats();
        this.heartbeatTimer = setTimeout(() => this.sendHeartbeat(), this.heartbeatIntervalMs);
      }
      teardown(callback, code, reason) {
        if (!this.conn) {
          return callback && callback();
        }
        const connToClose = this.conn;
        this.waitForBufferDone(connToClose, () => {
          if (code) {
            connToClose.close(code, reason || "");
          } else {
            connToClose.close();
          }
          this.waitForSocketClosed(connToClose, () => {
            if (this.conn === connToClose) {
              this.conn.onopen = function() {
              };
              this.conn.onerror = function() {
              };
              this.conn.onmessage = function() {
              };
              this.conn.onclose = function() {
              };
              this.conn = null;
            }
            callback && callback();
          });
        });
      }
      waitForBufferDone(conn, callback, tries = 1) {
        if (tries === 5 || !conn.bufferedAmount) {
          callback();
          return;
        }
        setTimeout(() => {
          this.waitForBufferDone(conn, callback, tries + 1);
        }, 150 * tries);
      }
      waitForSocketClosed(conn, callback, tries = 1) {
        if (tries === 5 || conn.readyState === SOCKET_STATES.closed) {
          callback();
          return;
        }
        setTimeout(() => {
          this.waitForSocketClosed(conn, callback, tries + 1);
        }, 150 * tries);
      }
      /**
      * @param {CloseEvent} event
      */
      onConnClose(event) {
        if (this.conn) this.conn.onclose = () => {
        };
        if (this.hasLogger()) this.log("transport", "close", event);
        this.triggerChanError();
        this.clearHeartbeats();
        if (!this.closeWasClean) {
          this.reconnectTimer.scheduleTimeout();
        }
        this.triggerStateCallbacks("close", event);
      }
      /**
       * @private
       * @param {Event} error
       */
      onConnError(error) {
        if (this.hasLogger()) this.log("transport", error);
        let transportBefore = this.transport;
        let establishedBefore = this.establishedConnections;
        this.triggerStateCallbacks("error", error, transportBefore, establishedBefore);
        if (transportBefore === this.transport || establishedBefore > 0) {
          this.triggerChanError();
        }
      }
      /**
       * @private
       */
      triggerChanError() {
        this.channels.forEach((channel) => {
          if (!(channel.isErrored() || channel.isLeaving() || channel.isClosed())) {
            channel.trigger(CHANNEL_EVENTS.error);
          }
        });
      }
      /**
       * @returns {string}
       */
      connectionState() {
        switch (this.conn && this.conn.readyState) {
          case SOCKET_STATES.connecting:
            return "connecting";
          case SOCKET_STATES.open:
            return "open";
          case SOCKET_STATES.closing:
            return "closing";
          default:
            return "closed";
        }
      }
      /**
       * @returns {boolean}
       */
      isConnected() {
        return this.connectionState() === "open";
      }
      /**
       *
       * @param {Channel} channel
       */
      remove(channel) {
        this.off(channel.stateChangeRefs);
        this.channels = this.channels.filter((c) => c !== channel);
      }
      /**
       * Removes `onOpen`, `onClose`, `onError,` and `onMessage` registrations.
       *
       * @param {string[]} refs - list of refs returned by calls to
       *                 `onOpen`, `onClose`, `onError,` and `onMessage`
       */
      off(refs) {
        for (let key in this.stateChangeCallbacks) {
          this.stateChangeCallbacks[key] = this.stateChangeCallbacks[key].filter(([ref]) => {
            return refs.indexOf(ref) === -1;
          });
        }
      }
      /**
       * Initiates a new channel for the given topic
       *
       * @param {string} topic
       * @param {Params | (() => Params)} [chanParams]- Parameters for the channel
       * @returns {Channel}
       */
      channel(topic, chanParams = {}) {
        let chan = new Channel(topic, chanParams, this);
        this.channels.push(chan);
        return chan;
      }
      /**
       * @param {Message<Record<string, any>>} data
       */
      push(data) {
        if (this.hasLogger()) {
          let { topic, event, payload, ref, join_ref } = data;
          this.log("push", `${topic} ${event} (${join_ref}, ${ref})`, payload);
        }
        if (this.isConnected()) {
          this.encode(data, (result) => this.conn.send(result));
        } else {
          this.sendBuffer.push(() => this.encode(data, (result) => this.conn.send(result)));
        }
      }
      /**
       * Return the next message ref, accounting for overflows
       * @returns {string}
       */
      makeRef() {
        let newRef = this.ref + 1;
        if (newRef === this.ref) {
          this.ref = 0;
        } else {
          this.ref = newRef;
        }
        return this.ref.toString();
      }
      sendHeartbeat() {
        if (!this.isConnected()) {
          try {
            this.heartbeatCallback("disconnected");
          } catch (e) {
            this.log("error", "error in heartbeat callback", e);
          }
          return;
        }
        if (this.pendingHeartbeatRef) {
          this.heartbeatTimeout();
          return;
        }
        this.pendingHeartbeatRef = this.makeRef();
        this.heartbeatSentAt = Date.now();
        this.push({ topic: "phoenix", event: "heartbeat", payload: {}, ref: this.pendingHeartbeatRef });
        try {
          this.heartbeatCallback("sent");
        } catch (e) {
          this.log("error", "error in heartbeat callback", e);
        }
        this.heartbeatTimeoutTimer = setTimeout(() => this.heartbeatTimeout(), this.heartbeatIntervalMs);
      }
      flushSendBuffer() {
        if (this.isConnected() && this.sendBuffer.length > 0) {
          this.sendBuffer.forEach((callback) => callback());
          this.sendBuffer = [];
        }
      }
      /**
      * @param {MessageEvent<any>} rawMessage
      */
      onConnMessage(rawMessage) {
        this.decode(rawMessage.data, (msg) => {
          let { topic, event, payload, ref, join_ref } = msg;
          if (ref && ref === this.pendingHeartbeatRef) {
            const latency = this.heartbeatSentAt ? Date.now() - this.heartbeatSentAt : void 0;
            this.clearHeartbeats();
            try {
              this.heartbeatCallback(payload.status === "ok" ? "ok" : "error", latency);
            } catch (e) {
              this.log("error", "error in heartbeat callback", e);
            }
            this.pendingHeartbeatRef = null;
            this.heartbeatSentAt = null;
            if (this.autoSendHeartbeat) {
              this.heartbeatTimer = setTimeout(() => this.sendHeartbeat(), this.heartbeatIntervalMs);
            }
          }
          if (this.hasLogger()) this.log("receive", `${payload.status || ""} ${topic} ${event} ${ref && "(" + ref + ")" || ""}`.trim(), payload);
          for (let i = 0; i < this.channels.length; i++) {
            const channel = this.channels[i];
            if (!channel.isMember(topic, event, payload, join_ref)) {
              continue;
            }
            channel.trigger(event, payload, ref, join_ref);
          }
          this.triggerStateCallbacks("message", msg);
        });
      }
      /**
       * @private
       * @template {keyof SocketStateChangeCallbacks} K
       * @param {K} event
       * @param {...Parameters<SocketStateChangeCallbacks[K][number][1]>} args
       * @returns {void}
       */
      triggerStateCallbacks(event, ...args) {
        try {
          this.stateChangeCallbacks[event].forEach(([_, callback]) => {
            try {
              callback(...args);
            } catch (e) {
              this.log("error", `error in ${event} callback`, e);
            }
          });
        } catch (e) {
          this.log("error", `error triggering ${event} callbacks`, e);
        }
      }
      leaveOpenTopic(topic) {
        let dupChannel = this.channels.find((c) => c.topic === topic && (c.isJoined() || c.isJoining()));
        if (dupChannel) {
          if (this.hasLogger()) this.log("transport", `leaving duplicate topic "${topic}"`);
          dupChannel.leave();
        }
      }
    };
  }
});

// design/node_modules/@supabase/realtime-js/dist/main/phoenix/presenceAdapter.js
var require_presenceAdapter = __commonJS({
  "design/node_modules/@supabase/realtime-js/dist/main/phoenix/presenceAdapter.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    var phoenix_1 = require_phoenix_cjs();
    var PresenceAdapter = class _PresenceAdapter {
      constructor(channel, opts) {
        const phoenixOptions = phoenixPresenceOptions(opts);
        this.presence = new phoenix_1.Presence(channel.getChannel(), phoenixOptions);
        this.presence.onJoin((key, currentPresence, newPresence) => {
          const onJoinPayload = _PresenceAdapter.onJoinPayload(key, currentPresence, newPresence);
          channel.getChannel().trigger("presence", onJoinPayload);
        });
        this.presence.onLeave((key, currentPresence, leftPresence) => {
          const onLeavePayload = _PresenceAdapter.onLeavePayload(key, currentPresence, leftPresence);
          channel.getChannel().trigger("presence", onLeavePayload);
        });
        this.presence.onSync(() => {
          channel.getChannel().trigger("presence", { event: "sync" });
        });
      }
      get state() {
        return _PresenceAdapter.transformState(this.presence.state);
      }
      /**
       * @private
       * Remove 'metas' key
       * Change 'phx_ref' to 'presence_ref'
       * Remove 'phx_ref' and 'phx_ref_prev'
       *
       * @example Transform state
       * // returns {
       *  abc123: [
       *    { presence_ref: '2', user_id: 1 },
       *    { presence_ref: '3', user_id: 2 }
       *  ]
       * }
       * RealtimePresence.transformState({
       *  abc123: {
       *    metas: [
       *      { phx_ref: '2', phx_ref_prev: '1' user_id: 1 },
       *      { phx_ref: '3', user_id: 2 }
       *    ]
       *  }
       * })
       *
       */
      static transformState(state) {
        state = cloneState(state);
        return Object.getOwnPropertyNames(state).reduce((newState, key) => {
          const presences = state[key];
          newState[key] = transformState(presences);
          return newState;
        }, {});
      }
      static onJoinPayload(key, currentPresence, newPresence) {
        const currentPresences = parseCurrentPresences(currentPresence);
        const newPresences = transformState(newPresence);
        return {
          event: "join",
          key,
          currentPresences,
          newPresences
        };
      }
      static onLeavePayload(key, currentPresence, leftPresence) {
        const currentPresences = parseCurrentPresences(currentPresence);
        const leftPresences = transformState(leftPresence);
        return {
          event: "leave",
          key,
          currentPresences,
          leftPresences
        };
      }
    };
    exports2.default = PresenceAdapter;
    function transformState(presences) {
      return presences.metas.map((presence) => {
        presence["presence_ref"] = presence["phx_ref"];
        delete presence["phx_ref"];
        delete presence["phx_ref_prev"];
        return presence;
      });
    }
    function cloneState(state) {
      return JSON.parse(JSON.stringify(state));
    }
    function phoenixPresenceOptions(opts) {
      return (opts === null || opts === void 0 ? void 0 : opts.events) && { events: opts.events };
    }
    function parseCurrentPresences(currentPresences) {
      return (currentPresences === null || currentPresences === void 0 ? void 0 : currentPresences.metas) ? transformState(currentPresences) : [];
    }
  }
});

// design/node_modules/@supabase/realtime-js/dist/main/RealtimePresence.js
var require_RealtimePresence = __commonJS({
  "design/node_modules/@supabase/realtime-js/dist/main/RealtimePresence.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.REALTIME_PRESENCE_LISTEN_EVENTS = void 0;
    var tslib_1 = (init_tslib_es6(), __toCommonJS(tslib_es6_exports));
    var presenceAdapter_1 = tslib_1.__importDefault(require_presenceAdapter());
    var REALTIME_PRESENCE_LISTEN_EVENTS;
    (function(REALTIME_PRESENCE_LISTEN_EVENTS2) {
      REALTIME_PRESENCE_LISTEN_EVENTS2["SYNC"] = "sync";
      REALTIME_PRESENCE_LISTEN_EVENTS2["JOIN"] = "join";
      REALTIME_PRESENCE_LISTEN_EVENTS2["LEAVE"] = "leave";
    })(REALTIME_PRESENCE_LISTEN_EVENTS || (exports2.REALTIME_PRESENCE_LISTEN_EVENTS = REALTIME_PRESENCE_LISTEN_EVENTS = {}));
    var RealtimePresence = class {
      get state() {
        return this.presenceAdapter.state;
      }
      /**
       * Creates a Presence helper that keeps the local presence state in sync with the server.
       *
       * @param channel - The realtime channel to bind to.
       * @param opts - Optional custom event names, e.g. `{ events: { state: 'state', diff: 'diff' } }`.
       *
       * @category Realtime
       *
       * @example Example for a presence channel
       * ```ts
       * const presence = new RealtimePresence(channel)
       *
       * channel.on('presence', ({ event, key }) => {
       *   console.log(`Presence ${event} on ${key}`)
       * })
       * ```
       */
      constructor(channel, opts) {
        this.channel = channel;
        this.presenceAdapter = new presenceAdapter_1.default(this.channel.channelAdapter, opts);
      }
    };
    exports2.default = RealtimePresence;
  }
});

// design/node_modules/@supabase/realtime-js/dist/main/phoenix/channelAdapter.js
var require_channelAdapter = __commonJS({
  "design/node_modules/@supabase/realtime-js/dist/main/phoenix/channelAdapter.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    var constants_1 = require_constants();
    var ChannelAdapter = class {
      constructor(socket, topic, params) {
        const phoenixParams = phoenixChannelParams(params);
        this.channel = socket.getSocket().channel(topic, phoenixParams);
        this.socket = socket;
      }
      get state() {
        return this.channel.state;
      }
      set state(state) {
        this.channel.state = state;
      }
      get joinedOnce() {
        return this.channel.joinedOnce;
      }
      get joinPush() {
        return this.channel.joinPush;
      }
      get rejoinTimer() {
        return this.channel.rejoinTimer;
      }
      on(event, callback) {
        return this.channel.on(event, callback);
      }
      off(event, refNumber) {
        this.channel.off(event, refNumber);
      }
      subscribe(timeout) {
        return this.channel.join(timeout);
      }
      unsubscribe(timeout) {
        return this.channel.leave(timeout);
      }
      teardown() {
        this.channel.teardown();
      }
      onClose(callback) {
        this.channel.onClose(callback);
      }
      onError(callback) {
        return this.channel.onError(callback);
      }
      push(event, payload, timeout) {
        let push;
        try {
          push = this.channel.push(event, payload, timeout);
        } catch (error) {
          throw new Error(`tried to push '${event}' to '${this.channel.topic}' before joining. Use channel.subscribe() before pushing events`);
        }
        if (this.channel.pushBuffer.length > constants_1.MAX_PUSH_BUFFER_SIZE) {
          const removedPush = this.channel.pushBuffer.shift();
          removedPush.cancelTimeout();
          this.socket.log("channel", `discarded push due to buffer overflow: ${removedPush.event}`, removedPush.payload());
        }
        return push;
      }
      updateJoinPayload(payload) {
        const oldPayload = this.channel.joinPush.payload();
        this.channel.joinPush.payload = () => Object.assign(Object.assign({}, oldPayload), payload);
      }
      canPush() {
        return this.socket.isConnected() && this.state === constants_1.CHANNEL_STATES.joined;
      }
      isJoined() {
        return this.state === constants_1.CHANNEL_STATES.joined;
      }
      isJoining() {
        return this.state === constants_1.CHANNEL_STATES.joining;
      }
      isClosed() {
        return this.state === constants_1.CHANNEL_STATES.closed;
      }
      isLeaving() {
        return this.state === constants_1.CHANNEL_STATES.leaving;
      }
      updateFilterBindings(filterBindings) {
        this.channel.filterBindings = filterBindings;
      }
      updatePayloadTransform(callback) {
        this.channel.onMessage = callback;
      }
      /**
       * @internal
       */
      getChannel() {
        return this.channel;
      }
    };
    exports2.default = ChannelAdapter;
    function phoenixChannelParams(options) {
      return {
        config: Object.assign({
          broadcast: { ack: false, self: false },
          presence: { key: "", enabled: false },
          private: false
        }, options.config)
      };
    }
  }
});

// design/node_modules/@supabase/realtime-js/dist/main/RealtimeChannel.js
var require_RealtimeChannel = __commonJS({
  "design/node_modules/@supabase/realtime-js/dist/main/RealtimeChannel.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.REALTIME_CHANNEL_STATES = exports2.REALTIME_SUBSCRIBE_STATES = exports2.REALTIME_LISTEN_TYPES = exports2.REALTIME_POSTGRES_CHANGES_LISTEN_EVENT = void 0;
    var tslib_1 = (init_tslib_es6(), __toCommonJS(tslib_es6_exports));
    var constants_1 = require_constants();
    var RealtimePresence_1 = tslib_1.__importDefault(require_RealtimePresence());
    var Transformers = tslib_1.__importStar(require_transformers());
    var transformers_1 = require_transformers();
    var channelAdapter_1 = tslib_1.__importDefault(require_channelAdapter());
    var REALTIME_POSTGRES_CHANGES_LISTEN_EVENT;
    (function(REALTIME_POSTGRES_CHANGES_LISTEN_EVENT2) {
      REALTIME_POSTGRES_CHANGES_LISTEN_EVENT2["ALL"] = "*";
      REALTIME_POSTGRES_CHANGES_LISTEN_EVENT2["INSERT"] = "INSERT";
      REALTIME_POSTGRES_CHANGES_LISTEN_EVENT2["UPDATE"] = "UPDATE";
      REALTIME_POSTGRES_CHANGES_LISTEN_EVENT2["DELETE"] = "DELETE";
    })(REALTIME_POSTGRES_CHANGES_LISTEN_EVENT || (exports2.REALTIME_POSTGRES_CHANGES_LISTEN_EVENT = REALTIME_POSTGRES_CHANGES_LISTEN_EVENT = {}));
    var REALTIME_LISTEN_TYPES;
    (function(REALTIME_LISTEN_TYPES2) {
      REALTIME_LISTEN_TYPES2["BROADCAST"] = "broadcast";
      REALTIME_LISTEN_TYPES2["PRESENCE"] = "presence";
      REALTIME_LISTEN_TYPES2["POSTGRES_CHANGES"] = "postgres_changes";
      REALTIME_LISTEN_TYPES2["SYSTEM"] = "system";
    })(REALTIME_LISTEN_TYPES || (exports2.REALTIME_LISTEN_TYPES = REALTIME_LISTEN_TYPES = {}));
    var REALTIME_SUBSCRIBE_STATES;
    (function(REALTIME_SUBSCRIBE_STATES2) {
      REALTIME_SUBSCRIBE_STATES2["SUBSCRIBED"] = "SUBSCRIBED";
      REALTIME_SUBSCRIBE_STATES2["TIMED_OUT"] = "TIMED_OUT";
      REALTIME_SUBSCRIBE_STATES2["CLOSED"] = "CLOSED";
      REALTIME_SUBSCRIBE_STATES2["CHANNEL_ERROR"] = "CHANNEL_ERROR";
    })(REALTIME_SUBSCRIBE_STATES || (exports2.REALTIME_SUBSCRIBE_STATES = REALTIME_SUBSCRIBE_STATES = {}));
    exports2.REALTIME_CHANNEL_STATES = constants_1.CHANNEL_STATES;
    var RealtimeChannel = class _RealtimeChannel {
      get state() {
        return this.channelAdapter.state;
      }
      set state(state) {
        this.channelAdapter.state = state;
      }
      get joinedOnce() {
        return this.channelAdapter.joinedOnce;
      }
      get timeout() {
        return this.socket.timeout;
      }
      get joinPush() {
        return this.channelAdapter.joinPush;
      }
      get rejoinTimer() {
        return this.channelAdapter.rejoinTimer;
      }
      /**
       * Creates a channel that can broadcast messages, sync presence, and listen to Postgres changes.
       *
       * The topic determines which realtime stream you are subscribing to. Config options let you
       * enable acknowledgement for broadcasts, presence tracking, or private channels.
       *
       * @category Realtime
       *
       * @example Using supabase-js (recommended)
       * ```ts
       * import { createClient } from '@supabase/supabase-js'
       *
       * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key')
       * const channel = supabase.channel('room1')
       * channel
       *   .on('broadcast', { event: 'cursor-pos' }, (payload) => console.log(payload))
       *   .subscribe()
       * ```
       *
       * @example Standalone import for bundle-sensitive environments
       * ```ts
       * import RealtimeClient from '@supabase/realtime-js'
       *
       * const client = new RealtimeClient('https://xyzcompany.supabase.co/realtime/v1', {
       *   params: { apikey: 'publishable-or-anon-key' },
       * })
       * const channel = new RealtimeChannel('realtime:public:messages', { config: {} }, client)
       * ```
       */
      constructor(topic, params = { config: {} }, socket) {
        var _a, _b;
        this.topic = topic;
        this.params = params;
        this.socket = socket;
        this.bindings = {};
        this.subTopic = topic.replace(/^realtime:/i, "");
        this.params.config = Object.assign({
          broadcast: { ack: false, self: false },
          presence: { key: "", enabled: false },
          private: false
        }, params.config);
        this.channelAdapter = new channelAdapter_1.default(this.socket.socketAdapter, topic, this.params);
        this.presence = new RealtimePresence_1.default(this);
        this._onClose(() => {
          this.socket._remove(this);
        });
        this._updateFilterTransform();
        this.broadcastEndpointURL = (0, transformers_1.httpEndpointURL)(this.socket.socketAdapter.endPointURL());
        this.private = this.params.config.private || false;
        if (!this.private && ((_b = (_a = this.params.config) === null || _a === void 0 ? void 0 : _a.broadcast) === null || _b === void 0 ? void 0 : _b.replay)) {
          throw new Error(`tried to use replay on public channel '${this.topic}'. It must be a private channel.`);
        }
      }
      /**
       * Subscribe registers your client with the server
       * @category Realtime
       */
      subscribe(callback, timeout = this.timeout) {
        var _a, _b, _c;
        if (!this.socket.isConnected()) {
          this.socket.connect();
        }
        if (this.channelAdapter.isClosed()) {
          const { config: { broadcast, presence, private: isPrivate } } = this.params;
          const postgres_changes = (_b = (_a = this.bindings.postgres_changes) === null || _a === void 0 ? void 0 : _a.map((r) => r.filter)) !== null && _b !== void 0 ? _b : [];
          const presence_enabled = !!this.bindings[REALTIME_LISTEN_TYPES.PRESENCE] && this.bindings[REALTIME_LISTEN_TYPES.PRESENCE].length > 0 || ((_c = this.params.config.presence) === null || _c === void 0 ? void 0 : _c.enabled) === true;
          const accessTokenPayload = {};
          const config = {
            broadcast,
            presence: Object.assign(Object.assign({}, presence), { enabled: presence_enabled }),
            postgres_changes,
            private: isPrivate
          };
          if (this.socket.accessTokenValue) {
            accessTokenPayload.access_token = this.socket.accessTokenValue;
          }
          this._onError((reason) => {
            callback === null || callback === void 0 ? void 0 : callback(REALTIME_SUBSCRIBE_STATES.CHANNEL_ERROR, reason);
          });
          this._onClose(() => callback === null || callback === void 0 ? void 0 : callback(REALTIME_SUBSCRIBE_STATES.CLOSED));
          this.updateJoinPayload(Object.assign({ config }, accessTokenPayload));
          this._updateFilterMessage();
          this.channelAdapter.subscribe(timeout).receive("ok", async ({ postgres_changes: postgres_changes2 }) => {
            if (!this.socket._isManualToken()) {
              this.socket.setAuth();
            }
            if (postgres_changes2 === void 0) {
              callback === null || callback === void 0 ? void 0 : callback(REALTIME_SUBSCRIBE_STATES.SUBSCRIBED);
              return;
            }
            this._updatePostgresBindings(postgres_changes2, callback);
          }).receive("error", (error) => {
            this.state = constants_1.CHANNEL_STATES.errored;
            callback === null || callback === void 0 ? void 0 : callback(REALTIME_SUBSCRIBE_STATES.CHANNEL_ERROR, new Error(JSON.stringify(Object.values(error).join(", ") || "error")));
          }).receive("timeout", () => {
            callback === null || callback === void 0 ? void 0 : callback(REALTIME_SUBSCRIBE_STATES.TIMED_OUT);
          });
        }
        return this;
      }
      _updatePostgresBindings(postgres_changes, callback) {
        var _a;
        const clientPostgresBindings = this.bindings.postgres_changes;
        const bindingsLen = (_a = clientPostgresBindings === null || clientPostgresBindings === void 0 ? void 0 : clientPostgresBindings.length) !== null && _a !== void 0 ? _a : 0;
        const newPostgresBindings = [];
        for (let i = 0; i < bindingsLen; i++) {
          const clientPostgresBinding = clientPostgresBindings[i];
          const { filter: { event, schema, table, filter } } = clientPostgresBinding;
          const serverPostgresFilter = postgres_changes && postgres_changes[i];
          if (serverPostgresFilter && serverPostgresFilter.event === event && _RealtimeChannel.isFilterValueEqual(serverPostgresFilter.schema, schema) && _RealtimeChannel.isFilterValueEqual(serverPostgresFilter.table, table) && _RealtimeChannel.isFilterValueEqual(serverPostgresFilter.filter, filter)) {
            newPostgresBindings.push(Object.assign(Object.assign({}, clientPostgresBinding), { id: serverPostgresFilter.id }));
          } else {
            this.unsubscribe();
            this.state = constants_1.CHANNEL_STATES.errored;
            callback === null || callback === void 0 ? void 0 : callback(REALTIME_SUBSCRIBE_STATES.CHANNEL_ERROR, new Error("mismatch between server and client bindings for postgres changes"));
            return;
          }
        }
        this.bindings.postgres_changes = newPostgresBindings;
        if (this.state != constants_1.CHANNEL_STATES.errored && callback) {
          callback(REALTIME_SUBSCRIBE_STATES.SUBSCRIBED);
        }
      }
      /**
       * Returns the current presence state for this channel.
       *
       * The shape is a map keyed by presence key (for example a user id) where each entry contains the
       * tracked metadata for that user.
       *
       * @category Realtime
       */
      presenceState() {
        return this.presence.state;
      }
      /**
       * Sends the supplied payload to the presence tracker so other subscribers can see that this
       * client is online. Use `untrack` to stop broadcasting presence for the same key.
       *
       * @category Realtime
       */
      async track(payload, opts = {}) {
        return await this.send({
          type: "presence",
          event: "track",
          payload
        }, opts.timeout || this.timeout);
      }
      /**
       * Removes the current presence state for this client.
       *
       * @category Realtime
       */
      async untrack(opts = {}) {
        return await this.send({
          type: "presence",
          event: "untrack"
        }, opts);
      }
      /**
       * Listen to realtime events on this channel.
       * @category Realtime
       *
       * @remarks
       * - By default, Broadcast and Presence are enabled for all projects.
       * - By default, listening to database changes is disabled for new projects due to database performance and security concerns. You can turn it on by managing Realtime's [replication](/docs/guides/api#realtime-api-overview).
       * - You can receive the "previous" data for updates and deletes by setting the table's `REPLICA IDENTITY` to `FULL` (e.g., `ALTER TABLE your_table REPLICA IDENTITY FULL;`).
       * - Row level security is not applied to delete statements. When RLS is enabled and replica identity is set to full, only the primary key is sent to clients.
       *
       * @example Listen to broadcast messages
       * ```js
       * const channel = supabase.channel("room1")
       *
       * channel.on("broadcast", { event: "cursor-pos" }, (payload) => {
       *   console.log("Cursor position received!", payload);
       * }).subscribe((status) => {
       *   if (status === "SUBSCRIBED") {
       *     channel.send({
       *       type: "broadcast",
       *       event: "cursor-pos",
       *       payload: { x: Math.random(), y: Math.random() },
       *     });
       *   }
       * });
       * ```
       *
       * @example Listen to presence sync
       * ```js
       * const channel = supabase.channel('room1')
       * channel
       *   .on('presence', { event: 'sync' }, () => {
       *     console.log('Synced presence state: ', channel.presenceState())
       *   })
       *   .subscribe(async (status) => {
       *     if (status === 'SUBSCRIBED') {
       *       await channel.track({ online_at: new Date().toISOString() })
       *     }
       *   })
       * ```
       *
       * @example Listen to presence join
       * ```js
       * const channel = supabase.channel('room1')
       * channel
       *   .on('presence', { event: 'join' }, ({ newPresences }) => {
       *     console.log('Newly joined presences: ', newPresences)
       *   })
       *   .subscribe(async (status) => {
       *     if (status === 'SUBSCRIBED') {
       *       await channel.track({ online_at: new Date().toISOString() })
       *     }
       *   })
       * ```
       *
       * @example Listen to presence leave
       * ```js
       * const channel = supabase.channel('room1')
       * channel
       *   .on('presence', { event: 'leave' }, ({ leftPresences }) => {
       *     console.log('Newly left presences: ', leftPresences)
       *   })
       *   .subscribe(async (status) => {
       *     if (status === 'SUBSCRIBED') {
       *       await channel.track({ online_at: new Date().toISOString() })
       *       await channel.untrack()
       *     }
       *   })
       * ```
       *
       * @example Listen to all database changes
       * ```js
       * supabase
       *   .channel('room1')
       *   .on('postgres_changes', { event: '*', schema: '*' }, payload => {
       *     console.log('Change received!', payload)
       *   })
       *   .subscribe()
       * ```
       *
       * @example Listen to a specific table
       * ```js
       * supabase
       *   .channel('room1')
       *   .on('postgres_changes', { event: '*', schema: 'public', table: 'countries' }, payload => {
       *     console.log('Change received!', payload)
       *   })
       *   .subscribe()
       * ```
       *
       * @example Listen to inserts
       * ```js
       * supabase
       *   .channel('room1')
       *   .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'countries' }, payload => {
       *     console.log('Change received!', payload)
       *   })
       *   .subscribe()
       * ```
       *
       * @exampleDescription Listen to updates
       * By default, Supabase will send only the updated record. If you want to receive the previous values as well you can
       * enable full replication for the table you are listening to:
       *
       * ```sql
       * alter table "your_table" replica identity full;
       * ```
       *
       * @example Listen to updates
       * ```js
       * supabase
       *   .channel('room1')
       *   .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'countries' }, payload => {
       *     console.log('Change received!', payload)
       *   })
       *   .subscribe()
       * ```
       *
       * @exampleDescription Listen to deletes
       * By default, Supabase does not send deleted records. If you want to receive the deleted record you can
       * enable full replication for the table you are listening to:
       *
       * ```sql
       * alter table "your_table" replica identity full;
       * ```
       *
       * @example Listen to deletes
       * ```js
       * supabase
       *   .channel('room1')
       *   .on('postgres_changes', { event: 'DELETE', schema: 'public', table: 'countries' }, payload => {
       *     console.log('Change received!', payload)
       *   })
       *   .subscribe()
       * ```
       *
       * @exampleDescription Listen to multiple events
       * You can chain listeners if you want to listen to multiple events for each table.
       *
       * @example Listen to multiple events
       * ```js
       * supabase
       *   .channel('room1')
       *   .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'countries' }, handleRecordInserted)
       *   .on('postgres_changes', { event: 'DELETE', schema: 'public', table: 'countries' }, handleRecordDeleted)
       *   .subscribe()
       * ```
       *
       * @exampleDescription Listen to row level changes
       * You can listen to individual rows using the format `{table}:{col}=eq.{val}` - where `{col}` is the column name, and `{val}` is the value which you want to match.
       *
       * @example Listen to row level changes
       * ```js
       * supabase
       *   .channel('room1')
       *   .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'countries', filter: 'id=eq.200' }, handleRecordUpdated)
       *   .subscribe()
       * ```
       */
      on(type, filter, callback) {
        const stateCheck = this.channelAdapter.isJoined() || this.channelAdapter.isJoining();
        const typeCheck = type === REALTIME_LISTEN_TYPES.PRESENCE || type === REALTIME_LISTEN_TYPES.POSTGRES_CHANGES;
        if (stateCheck && typeCheck) {
          this.socket.log("channel", `cannot add \`${type}\` callbacks for ${this.topic} after \`subscribe()\`.`);
          throw new Error(`cannot add \`${type}\` callbacks for ${this.topic} after \`subscribe()\`.`);
        }
        return this._on(type, filter, callback);
      }
      /**
       * Sends a broadcast message explicitly via REST API.
       *
       * This method always uses the REST API endpoint regardless of WebSocket connection state.
       * Useful when you want to guarantee REST delivery or when gradually migrating from implicit REST fallback.
       *
       * @param event The name of the broadcast event
       * @param payload Payload to be sent (required)
       * @param opts Options including timeout
       * @returns Promise resolving to object with success status, and error details if failed
       *
       * @category Realtime
       */
      async httpSend(event, payload, opts = {}) {
        var _a;
        if (payload === void 0 || payload === null) {
          return Promise.reject(new Error("Payload is required for httpSend()"));
        }
        const headers = {
          apikey: this.socket.apiKey ? this.socket.apiKey : "",
          "Content-Type": "application/json"
        };
        if (this.socket.accessTokenValue) {
          headers["Authorization"] = `Bearer ${this.socket.accessTokenValue}`;
        }
        const options = {
          method: "POST",
          headers,
          body: JSON.stringify({
            messages: [
              {
                topic: this.subTopic,
                event,
                payload,
                private: this.private
              }
            ]
          })
        };
        const response2 = await this._fetchWithTimeout(this.broadcastEndpointURL, options, (_a = opts.timeout) !== null && _a !== void 0 ? _a : this.timeout);
        if (response2.status === 202) {
          return { success: true };
        }
        let errorMessage = response2.statusText;
        try {
          const errorBody = await response2.json();
          errorMessage = errorBody.error || errorBody.message || errorMessage;
        } catch (_b) {
        }
        return Promise.reject(new Error(errorMessage));
      }
      /**
       * Sends a message into the channel.
       *
       * @param args Arguments to send to channel
       * @param args.type The type of event to send
       * @param args.event The name of the event being sent
       * @param args.payload Payload to be sent
       * @param opts Options to be used during the send process
       *
       * @category Realtime
       *
       * @remarks
       * - When using REST you don't need to subscribe to the channel
       * - REST calls are only available from 2.37.0 onwards
       *
       * @example Send a message via websocket
       * ```js
       * const channel = supabase.channel('room1')
       *
       * channel.subscribe((status) => {
       *   if (status === 'SUBSCRIBED') {
       *     channel.send({
       *       type: 'broadcast',
       *       event: 'cursor-pos',
       *       payload: { x: Math.random(), y: Math.random() },
       *     })
       *   }
       * })
       * ```
       *
       * @exampleResponse Send a message via websocket
       * ```js
       * ok | timed out | error
       * ```
       *
       * @example Send a message via REST
       * ```js
       * supabase
       *   .channel('room1')
       *   .httpSend('cursor-pos', { x: Math.random(), y: Math.random() })
       * ```
       */
      async send(args, opts = {}) {
        var _a, _b;
        if (!this.channelAdapter.canPush() && args.type === "broadcast") {
          console.warn("Realtime send() is automatically falling back to REST API. This behavior will be deprecated in the future. Please use httpSend() explicitly for REST delivery.");
          const { event, payload: endpoint_payload } = args;
          const headers = {
            apikey: this.socket.apiKey ? this.socket.apiKey : "",
            "Content-Type": "application/json"
          };
          if (this.socket.accessTokenValue) {
            headers["Authorization"] = `Bearer ${this.socket.accessTokenValue}`;
          }
          const options = {
            method: "POST",
            headers,
            body: JSON.stringify({
              messages: [
                {
                  topic: this.subTopic,
                  event,
                  payload: endpoint_payload,
                  private: this.private
                }
              ]
            })
          };
          try {
            const response2 = await this._fetchWithTimeout(this.broadcastEndpointURL, options, (_a = opts.timeout) !== null && _a !== void 0 ? _a : this.timeout);
            await ((_b = response2.body) === null || _b === void 0 ? void 0 : _b.cancel());
            return response2.ok ? "ok" : "error";
          } catch (error) {
            if (error.name === "AbortError") {
              return "timed out";
            } else {
              return "error";
            }
          }
        } else {
          return new Promise((resolve) => {
            var _a2, _b2, _c;
            const push = this.channelAdapter.push(args.type, args, opts.timeout || this.timeout);
            if (args.type === "broadcast" && !((_c = (_b2 = (_a2 = this.params) === null || _a2 === void 0 ? void 0 : _a2.config) === null || _b2 === void 0 ? void 0 : _b2.broadcast) === null || _c === void 0 ? void 0 : _c.ack)) {
              resolve("ok");
            }
            push.receive("ok", () => resolve("ok"));
            push.receive("error", () => resolve("error"));
            push.receive("timeout", () => resolve("timed out"));
          });
        }
      }
      /**
       * Updates the payload that will be sent the next time the channel joins (reconnects).
       * Useful for rotating access tokens or updating config without re-creating the channel.
       *
       * @category Realtime
       */
      updateJoinPayload(payload) {
        this.channelAdapter.updateJoinPayload(payload);
      }
      /**
       * Leaves the channel.
       *
       * Unsubscribes from server events, and instructs channel to terminate on server.
       * Triggers onClose() hooks.
       *
       * To receive leave acknowledgements, use the a `receive` hook to bind to the server ack, ie:
       * channel.unsubscribe().receive("ok", () => alert("left!") )
       *
       * @category Realtime
       */
      async unsubscribe(timeout = this.timeout) {
        return new Promise((resolve) => {
          this.channelAdapter.unsubscribe(timeout).receive("ok", () => resolve("ok")).receive("timeout", () => resolve("timed out")).receive("error", () => resolve("error"));
        });
      }
      /**
       * Destroys and stops related timers.
       *
       * @category Realtime
       */
      teardown() {
        this.channelAdapter.teardown();
      }
      /** @internal */
      async _fetchWithTimeout(url, options, timeout) {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeout);
        const response2 = await this.socket.fetch(url, Object.assign(Object.assign({}, options), { signal: controller.signal }));
        clearTimeout(id);
        return response2;
      }
      /** @internal */
      _on(type, filter, callback) {
        const typeLower = type.toLocaleLowerCase();
        const ref = this.channelAdapter.on(type, callback);
        const binding = {
          type: typeLower,
          filter,
          callback,
          ref
        };
        if (this.bindings[typeLower]) {
          this.bindings[typeLower].push(binding);
        } else {
          this.bindings[typeLower] = [binding];
        }
        this._updateFilterMessage();
        return this;
      }
      /**
       * Registers a callback that will be executed when the channel closes.
       *
       * @internal
       */
      _onClose(callback) {
        this.channelAdapter.onClose(callback);
      }
      /**
       * Registers a callback that will be executed when the channel encounteres an error.
       *
       * @internal
       */
      _onError(callback) {
        this.channelAdapter.onError(callback);
      }
      /** @internal */
      _updateFilterMessage() {
        this.channelAdapter.updateFilterBindings((binding, payload, ref) => {
          var _a, _b, _c, _d, _e, _f, _g;
          const typeLower = binding.event.toLocaleLowerCase();
          if (this._notThisChannelEvent(typeLower, ref)) {
            return false;
          }
          const bind = (_a = this.bindings[typeLower]) === null || _a === void 0 ? void 0 : _a.find((bind2) => bind2.ref === binding.ref);
          if (!bind) {
            return true;
          }
          if (["broadcast", "presence", "postgres_changes"].includes(typeLower)) {
            if ("id" in bind) {
              const bindId = bind.id;
              const bindEvent = (_b = bind.filter) === null || _b === void 0 ? void 0 : _b.event;
              return bindId && ((_c = payload.ids) === null || _c === void 0 ? void 0 : _c.includes(bindId)) && (bindEvent === "*" || (bindEvent === null || bindEvent === void 0 ? void 0 : bindEvent.toLocaleLowerCase()) === ((_d = payload.data) === null || _d === void 0 ? void 0 : _d.type.toLocaleLowerCase()));
            } else {
              const bindEvent = (_f = (_e = bind === null || bind === void 0 ? void 0 : bind.filter) === null || _e === void 0 ? void 0 : _e.event) === null || _f === void 0 ? void 0 : _f.toLocaleLowerCase();
              return bindEvent === "*" || bindEvent === ((_g = payload === null || payload === void 0 ? void 0 : payload.event) === null || _g === void 0 ? void 0 : _g.toLocaleLowerCase());
            }
          } else {
            return bind.type.toLocaleLowerCase() === typeLower;
          }
        });
      }
      /** @internal */
      _notThisChannelEvent(event, ref) {
        const { close, error, leave, join } = constants_1.CHANNEL_EVENTS;
        const events = [close, error, leave, join];
        return ref && events.includes(event) && ref !== this.joinPush.ref;
      }
      /** @internal */
      _updateFilterTransform() {
        this.channelAdapter.updatePayloadTransform((event, payload, ref) => {
          if (typeof payload === "object" && "ids" in payload) {
            const postgresChanges = payload.data;
            const { schema, table, commit_timestamp, type, errors } = postgresChanges;
            const enrichedPayload = {
              schema,
              table,
              commit_timestamp,
              eventType: type,
              new: {},
              old: {},
              errors
            };
            return Object.assign(Object.assign({}, enrichedPayload), this._getPayloadRecords(postgresChanges));
          }
          return payload;
        });
      }
      copyBindings(other) {
        if (this.joinedOnce) {
          throw new Error("cannot copy bindings into joined channel");
        }
        for (const kind in other.bindings) {
          for (const binding of other.bindings[kind]) {
            this._on(binding.type, binding.filter, binding.callback);
          }
        }
      }
      /**
       * Compares two optional filter values for equality.
       * Treats undefined, null, and empty string as equivalent empty values.
       * @internal
       */
      static isFilterValueEqual(serverValue, clientValue) {
        const normalizedServer = serverValue !== null && serverValue !== void 0 ? serverValue : void 0;
        const normalizedClient = clientValue !== null && clientValue !== void 0 ? clientValue : void 0;
        return normalizedServer === normalizedClient;
      }
      /** @internal */
      _getPayloadRecords(payload) {
        const records = {
          new: {},
          old: {}
        };
        if (payload.type === "INSERT" || payload.type === "UPDATE") {
          records.new = Transformers.convertChangeData(payload.columns, payload.record);
        }
        if (payload.type === "UPDATE" || payload.type === "DELETE") {
          records.old = Transformers.convertChangeData(payload.columns, payload.old_record);
        }
        return records;
      }
    };
    exports2.default = RealtimeChannel;
  }
});

// design/node_modules/@supabase/realtime-js/dist/main/phoenix/socketAdapter.js
var require_socketAdapter = __commonJS({
  "design/node_modules/@supabase/realtime-js/dist/main/phoenix/socketAdapter.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    var phoenix_1 = require_phoenix_cjs();
    var constants_1 = require_constants();
    var SocketAdapter = class {
      constructor(endPoint, options) {
        this.socket = new phoenix_1.Socket(endPoint, options);
      }
      get timeout() {
        return this.socket.timeout;
      }
      get endPoint() {
        return this.socket.endPoint;
      }
      get transport() {
        return this.socket.transport;
      }
      get heartbeatIntervalMs() {
        return this.socket.heartbeatIntervalMs;
      }
      get heartbeatCallback() {
        return this.socket.heartbeatCallback;
      }
      set heartbeatCallback(callback) {
        this.socket.heartbeatCallback = callback;
      }
      get heartbeatTimer() {
        return this.socket.heartbeatTimer;
      }
      get pendingHeartbeatRef() {
        return this.socket.pendingHeartbeatRef;
      }
      get reconnectTimer() {
        return this.socket.reconnectTimer;
      }
      get vsn() {
        return this.socket.vsn;
      }
      get encode() {
        return this.socket.encode;
      }
      get decode() {
        return this.socket.decode;
      }
      get reconnectAfterMs() {
        return this.socket.reconnectAfterMs;
      }
      get sendBuffer() {
        return this.socket.sendBuffer;
      }
      get stateChangeCallbacks() {
        return this.socket.stateChangeCallbacks;
      }
      connect() {
        this.socket.connect();
      }
      disconnect(callback, code, reason, timeout = 1e4) {
        return new Promise((resolve) => {
          setTimeout(() => resolve("timeout"), timeout);
          this.socket.disconnect(() => {
            callback();
            resolve("ok");
          }, code, reason);
        });
      }
      push(data) {
        this.socket.push(data);
      }
      log(kind, msg, data) {
        this.socket.log(kind, msg, data);
      }
      makeRef() {
        return this.socket.makeRef();
      }
      onOpen(callback) {
        this.socket.onOpen(callback);
      }
      onClose(callback) {
        this.socket.onClose(callback);
      }
      onError(callback) {
        this.socket.onError(callback);
      }
      onMessage(callback) {
        this.socket.onMessage(callback);
      }
      isConnected() {
        return this.socket.isConnected();
      }
      isConnecting() {
        return this.socket.connectionState() == constants_1.CONNECTION_STATE.connecting;
      }
      isDisconnecting() {
        return this.socket.connectionState() == constants_1.CONNECTION_STATE.closing;
      }
      connectionState() {
        return this.socket.connectionState();
      }
      endPointURL() {
        return this.socket.endPointURL();
      }
      sendHeartbeat() {
        this.socket.sendHeartbeat();
      }
      /**
       * @internal
       */
      getSocket() {
        return this.socket;
      }
    };
    exports2.default = SocketAdapter;
  }
});

// design/node_modules/@supabase/realtime-js/dist/main/RealtimeClient.js
var require_RealtimeClient = __commonJS({
  "design/node_modules/@supabase/realtime-js/dist/main/RealtimeClient.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    var tslib_1 = (init_tslib_es6(), __toCommonJS(tslib_es6_exports));
    var websocket_factory_1 = tslib_1.__importDefault(require_websocket_factory());
    var constants_1 = require_constants();
    var serializer_1 = tslib_1.__importDefault(require_serializer());
    var transformers_1 = require_transformers();
    var RealtimeChannel_1 = tslib_1.__importDefault(require_RealtimeChannel());
    var socketAdapter_1 = tslib_1.__importDefault(require_socketAdapter());
    var CONNECTION_TIMEOUTS = {
      HEARTBEAT_INTERVAL: 25e3,
      RECONNECT_DELAY: 10,
      HEARTBEAT_TIMEOUT_FALLBACK: 100
    };
    var RECONNECT_INTERVALS = [1e3, 2e3, 5e3, 1e4];
    var DEFAULT_RECONNECT_FALLBACK = 1e4;
    var WORKER_SCRIPT = `
  addEventListener("message", (e) => {
    if (e.data.event === "start") {
      setInterval(() => postMessage({ event: "keepAlive" }), e.data.interval);
    }
  });`;
    var RealtimeClient2 = class {
      get endPoint() {
        return this.socketAdapter.endPoint;
      }
      get timeout() {
        return this.socketAdapter.timeout;
      }
      get transport() {
        return this.socketAdapter.transport;
      }
      get heartbeatCallback() {
        return this.socketAdapter.heartbeatCallback;
      }
      get heartbeatIntervalMs() {
        return this.socketAdapter.heartbeatIntervalMs;
      }
      get heartbeatTimer() {
        if (this.worker) {
          return this._workerHeartbeatTimer;
        }
        return this.socketAdapter.heartbeatTimer;
      }
      get pendingHeartbeatRef() {
        if (this.worker) {
          return this._pendingWorkerHeartbeatRef;
        }
        return this.socketAdapter.pendingHeartbeatRef;
      }
      get reconnectTimer() {
        return this.socketAdapter.reconnectTimer;
      }
      get vsn() {
        return this.socketAdapter.vsn;
      }
      get encode() {
        return this.socketAdapter.encode;
      }
      get decode() {
        return this.socketAdapter.decode;
      }
      get reconnectAfterMs() {
        return this.socketAdapter.reconnectAfterMs;
      }
      get sendBuffer() {
        return this.socketAdapter.sendBuffer;
      }
      get stateChangeCallbacks() {
        return this.socketAdapter.stateChangeCallbacks;
      }
      /**
       * Initializes the Socket.
       *
       * @param endPoint The string WebSocket endpoint, ie, "ws://example.com/socket", "wss://example.com", "/socket" (inherited host & protocol)
       * @param httpEndpoint The string HTTP endpoint, ie, "https://example.com", "/" (inherited host & protocol)
       * @param options.transport The Websocket Transport, for example WebSocket. This can be a custom implementation
       * @param options.timeout The default timeout in milliseconds to trigger push timeouts.
       * @param options.params The optional params to pass when connecting.
       * @param options.headers Deprecated: headers cannot be set on websocket connections and this option will be removed in the future.
       * @param options.heartbeatIntervalMs The millisec interval to send a heartbeat message.
       * @param options.heartbeatCallback The optional function to handle heartbeat status and latency.
       * @param options.logger The optional function for specialized logging, ie: logger: (kind, msg, data) => { console.log(`${kind}: ${msg}`, data) }
       * @param options.logLevel Sets the log level for Realtime
       * @param options.encode The function to encode outgoing messages. Defaults to JSON: (payload, callback) => callback(JSON.stringify(payload))
       * @param options.decode The function to decode incoming messages. Defaults to Serializer's decode.
       * @param options.reconnectAfterMs he optional function that returns the millsec reconnect interval. Defaults to stepped backoff off.
       * @param options.worker Use Web Worker to set a side flow. Defaults to false.
       * @param options.workerUrl The URL of the worker script. Defaults to https://realtime.supabase.com/worker.js that includes a heartbeat event call to keep the connection alive.
       * @param options.vsn The protocol version to use when connecting. Supported versions are "1.0.0" and "2.0.0". Defaults to "2.0.0".
       *
       * @category Realtime
       *
       * @example Using supabase-js (recommended)
       * ```ts
       * import { createClient } from '@supabase/supabase-js'
       *
       * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key')
       * const channel = supabase.channel('room1')
       * channel
       *   .on('broadcast', { event: 'cursor-pos' }, (payload) => console.log(payload))
       *   .subscribe()
       * ```
       *
       * @example Standalone import for bundle-sensitive environments
       * ```ts
       * import RealtimeClient from '@supabase/realtime-js'
       *
       * const client = new RealtimeClient('https://xyzcompany.supabase.co/realtime/v1', {
       *   params: { apikey: 'publishable-or-anon-key' },
       * })
       * client.connect()
       * ```
       */
      constructor(endPoint, options) {
        var _a;
        this.channels = new Array();
        this.accessTokenValue = null;
        this.accessToken = null;
        this.apiKey = null;
        this.httpEndpoint = "";
        this.headers = {};
        this.params = {};
        this.ref = 0;
        this.serializer = new serializer_1.default();
        this._manuallySetToken = false;
        this._authPromise = null;
        this._workerHeartbeatTimer = void 0;
        this._pendingWorkerHeartbeatRef = null;
        this._resolveFetch = (customFetch) => {
          if (customFetch) {
            return (...args) => customFetch(...args);
          }
          return (...args) => fetch(...args);
        };
        if (!((_a = options === null || options === void 0 ? void 0 : options.params) === null || _a === void 0 ? void 0 : _a.apikey)) {
          throw new Error("API key is required to connect to Realtime");
        }
        this.apiKey = options.params.apikey;
        const socketAdapterOptions = this._initializeOptions(options);
        this.socketAdapter = new socketAdapter_1.default(endPoint, socketAdapterOptions);
        this.httpEndpoint = (0, transformers_1.httpEndpointURL)(endPoint);
        this.fetch = this._resolveFetch(options === null || options === void 0 ? void 0 : options.fetch);
      }
      /**
       * Connects the socket, unless already connected.
       *
       * @category Realtime
       */
      connect() {
        if (this.isConnecting() || this.isDisconnecting() || this.isConnected()) {
          return;
        }
        if (this.accessToken && !this._authPromise) {
          this._setAuthSafely("connect");
        }
        this._setupConnectionHandlers();
        try {
          this.socketAdapter.connect();
        } catch (error) {
          const errorMessage = error.message;
          if (errorMessage.includes("Node.js")) {
            throw new Error(`${errorMessage}

To use Realtime in Node.js, you need to provide a WebSocket implementation:

Option 1: Use Node.js 22+ which has native WebSocket support
Option 2: Install and provide the "ws" package:

  npm install ws

  import ws from "ws"
  const client = new RealtimeClient(url, {
    ...options,
    transport: ws
  })`);
          }
          throw new Error(`WebSocket not available: ${errorMessage}`);
        }
        this._handleNodeJsRaceCondition();
      }
      /**
       * Returns the URL of the websocket.
       * @returns string The URL of the websocket.
       *
       * @category Realtime
       */
      endpointURL() {
        return this.socketAdapter.endPointURL();
      }
      /**
       * Disconnects the socket.
       *
       * @param code A numeric status code to send on disconnect.
       * @param reason A custom reason for the disconnect.
       *
       * @category Realtime
       */
      async disconnect(code, reason) {
        if (this.isDisconnecting()) {
          return "ok";
        }
        return await this.socketAdapter.disconnect(() => {
          clearInterval(this._workerHeartbeatTimer);
          this._terminateWorker();
        }, code, reason);
      }
      /**
       * Returns all created channels
       *
       * @category Realtime
       */
      getChannels() {
        return this.channels;
      }
      /**
       * Unsubscribes, removes and tears down a single channel
       * @param channel A RealtimeChannel instance
       *
       * @category Realtime
       */
      async removeChannel(channel) {
        const status = await channel.unsubscribe();
        if (status === "ok") {
          channel.teardown();
        }
        if (this.channels.length === 0) {
          this.disconnect();
        }
        return status;
      }
      /**
       * Unsubscribes, removes and tears down all channels
       *
       * @category Realtime
       */
      async removeAllChannels() {
        const promises = this.channels.map(async (channel) => {
          const result2 = await channel.unsubscribe();
          channel.teardown();
          return result2;
        });
        const result = await Promise.all(promises);
        this.disconnect();
        return result;
      }
      /**
       * Logs the message.
       *
       * For customized logging, `this.logger` can be overridden in Client constructor.
       *
       * @category Realtime
       */
      log(kind, msg, data) {
        this.socketAdapter.log(kind, msg, data);
      }
      /**
       * Returns the current state of the socket.
       *
       * @category Realtime
       */
      connectionState() {
        return this.socketAdapter.connectionState() || constants_1.CONNECTION_STATE.closed;
      }
      /**
       * Returns `true` is the connection is open.
       *
       * @category Realtime
       */
      isConnected() {
        return this.socketAdapter.isConnected();
      }
      /**
       * Returns `true` if the connection is currently connecting.
       *
       * @category Realtime
       */
      isConnecting() {
        return this.socketAdapter.isConnecting();
      }
      /**
       * Returns `true` if the connection is currently disconnecting.
       *
       * @category Realtime
       */
      isDisconnecting() {
        return this.socketAdapter.isDisconnecting();
      }
      /**
       * Creates (or reuses) a {@link RealtimeChannel} for the provided topic.
       *
       * Topics are automatically prefixed with `realtime:` to match the Realtime service.
       * If a channel with the same topic already exists it will be returned instead of creating
       * a duplicate connection.
       *
       * @category Realtime
       */
      channel(topic, params = { config: {} }) {
        const realtimeTopic = `realtime:${topic}`;
        const exists = this.getChannels().find((c) => c.topic === realtimeTopic);
        if (!exists) {
          const chan = new RealtimeChannel_1.default(`realtime:${topic}`, params, this);
          this.channels.push(chan);
          return chan;
        } else {
          return exists;
        }
      }
      /**
       * Push out a message if the socket is connected.
       *
       * If the socket is not connected, the message gets enqueued within a local buffer, and sent out when a connection is next established.
       *
       * @category Realtime
       */
      push(data) {
        this.socketAdapter.push(data);
      }
      /**
       * Sets the JWT access token used for channel subscription authorization and Realtime RLS.
       *
       * If param is null it will use the `accessToken` callback function or the token set on the client.
       *
       * On callback used, it will set the value of the token internal to the client.
       *
       * When a token is explicitly provided, it will be preserved across channel operations
       * (including removeChannel and resubscribe). The `accessToken` callback will not be
       * invoked until `setAuth()` is called without arguments.
       *
       * @param token A JWT string to override the token set on the client.
       *
       * @example Setting the authorization header
       * // Use a manual token (preserved across resubscribes, ignores accessToken callback)
       * client.realtime.setAuth('my-custom-jwt')
       *
       * // Switch back to using the accessToken callback
       * client.realtime.setAuth()
       *
       * @category Realtime
       */
      async setAuth(token = null) {
        this._authPromise = this._performAuth(token);
        try {
          await this._authPromise;
        } finally {
          this._authPromise = null;
        }
      }
      /**
       * Returns true if the current access token was explicitly set via setAuth(token),
       * false if it was obtained via the accessToken callback.
       * @internal
       */
      _isManualToken() {
        return this._manuallySetToken;
      }
      /**
       * Sends a heartbeat message if the socket is connected.
       *
       * @category Realtime
       */
      async sendHeartbeat() {
        this.socketAdapter.sendHeartbeat();
      }
      /**
       * Sets a callback that receives lifecycle events for internal heartbeat messages.
       * Useful for instrumenting connection health (e.g. sent/ok/timeout/disconnected).
       *
       * @category Realtime
       */
      onHeartbeat(callback) {
        this.socketAdapter.heartbeatCallback = this._wrapHeartbeatCallback(callback);
      }
      /**
       * Return the next message ref, accounting for overflows
       *
       * @internal
       */
      _makeRef() {
        return this.socketAdapter.makeRef();
      }
      /**
       * Removes a channel from RealtimeClient
       *
       * @param channel An open subscription.
       *
       * @internal
       */
      _remove(channel) {
        this.channels = this.channels.filter((c) => c.topic !== channel.topic);
      }
      /**
       * Perform the actual auth operation
       * @internal
       */
      async _performAuth(token = null) {
        let tokenToSend;
        let isManualToken = false;
        if (token) {
          tokenToSend = token;
          isManualToken = true;
        } else if (this.accessToken) {
          try {
            tokenToSend = await this.accessToken();
          } catch (e) {
            this.log("error", "Error fetching access token from callback", e);
            tokenToSend = this.accessTokenValue;
          }
        } else {
          tokenToSend = this.accessTokenValue;
        }
        if (isManualToken) {
          this._manuallySetToken = true;
        } else if (this.accessToken) {
          this._manuallySetToken = false;
        }
        if (this.accessTokenValue != tokenToSend) {
          this.accessTokenValue = tokenToSend;
          this.channels.forEach((channel) => {
            const payload = {
              access_token: tokenToSend,
              version: constants_1.DEFAULT_VERSION
            };
            tokenToSend && channel.updateJoinPayload(payload);
            if (channel.joinedOnce && channel.channelAdapter.isJoined()) {
              channel.channelAdapter.push(constants_1.CHANNEL_EVENTS.access_token, {
                access_token: tokenToSend
              });
            }
          });
        }
      }
      /**
       * Wait for any in-flight auth operations to complete
       * @internal
       */
      async _waitForAuthIfNeeded() {
        if (this._authPromise) {
          await this._authPromise;
        }
      }
      /**
       * Safely call setAuth with standardized error handling
       * @internal
       */
      _setAuthSafely(context = "general") {
        if (!this._isManualToken()) {
          this.setAuth().catch((e) => {
            this.log("error", `Error setting auth in ${context}`, e);
          });
        }
      }
      /** @internal */
      _setupConnectionHandlers() {
        this.socketAdapter.onOpen(() => {
          const authPromise = this._authPromise || (this.accessToken && !this.accessTokenValue ? this.setAuth() : Promise.resolve());
          authPromise.catch((e) => {
            this.log("error", "error waiting for auth on connect", e);
          });
          if (this.worker && !this.workerRef) {
            this._startWorkerHeartbeat();
          }
        });
        this.socketAdapter.onClose(() => {
          if (this.worker && this.workerRef) {
            this._terminateWorker();
          }
        });
        this.socketAdapter.onMessage((message) => {
          if (message.ref && message.ref === this._pendingWorkerHeartbeatRef) {
            this._pendingWorkerHeartbeatRef = null;
          }
        });
      }
      /** @internal */
      _handleNodeJsRaceCondition() {
        if (this.socketAdapter.isConnected()) {
          this.socketAdapter.getSocket().onConnOpen();
        }
      }
      /** @internal */
      _wrapHeartbeatCallback(heartbeatCallback) {
        return (status, latency) => {
          if (status == "sent")
            this._setAuthSafely();
          if (heartbeatCallback)
            heartbeatCallback(status, latency);
        };
      }
      /** @internal */
      _startWorkerHeartbeat() {
        if (this.workerUrl) {
          this.log("worker", `starting worker for from ${this.workerUrl}`);
        } else {
          this.log("worker", `starting default worker`);
        }
        const objectUrl = this._workerObjectUrl(this.workerUrl);
        this.workerRef = new Worker(objectUrl);
        this.workerRef.onerror = (error) => {
          this.log("worker", "worker error", error.message);
          this._terminateWorker();
          this.disconnect();
        };
        this.workerRef.onmessage = (event) => {
          if (event.data.event === "keepAlive") {
            this.sendHeartbeat();
          }
        };
        this.workerRef.postMessage({
          event: "start",
          interval: this.heartbeatIntervalMs
        });
      }
      /**
       * Terminate the Web Worker and clear the reference
       * @internal
       */
      _terminateWorker() {
        if (this.workerRef) {
          this.log("worker", "terminating worker");
          this.workerRef.terminate();
          this.workerRef = void 0;
        }
      }
      /** @internal */
      _workerObjectUrl(url) {
        let result_url;
        if (url) {
          result_url = url;
        } else {
          const blob = new Blob([WORKER_SCRIPT], { type: "application/javascript" });
          result_url = URL.createObjectURL(blob);
        }
        return result_url;
      }
      /**
       * Initialize socket options with defaults
       * @internal
       */
      _initializeOptions(options) {
        var _a, _b, _c, _d, _e, _f, _g, _h, _j;
        this.worker = (_a = options === null || options === void 0 ? void 0 : options.worker) !== null && _a !== void 0 ? _a : false;
        this.accessToken = (_b = options === null || options === void 0 ? void 0 : options.accessToken) !== null && _b !== void 0 ? _b : null;
        const result = {};
        result.timeout = (_c = options === null || options === void 0 ? void 0 : options.timeout) !== null && _c !== void 0 ? _c : constants_1.DEFAULT_TIMEOUT;
        result.heartbeatIntervalMs = (_d = options === null || options === void 0 ? void 0 : options.heartbeatIntervalMs) !== null && _d !== void 0 ? _d : CONNECTION_TIMEOUTS.HEARTBEAT_INTERVAL;
        result.transport = (_e = options === null || options === void 0 ? void 0 : options.transport) !== null && _e !== void 0 ? _e : websocket_factory_1.default.getWebSocketConstructor();
        result.params = options === null || options === void 0 ? void 0 : options.params;
        result.logger = options === null || options === void 0 ? void 0 : options.logger;
        result.heartbeatCallback = this._wrapHeartbeatCallback(options === null || options === void 0 ? void 0 : options.heartbeatCallback);
        result.reconnectAfterMs = (_f = options === null || options === void 0 ? void 0 : options.reconnectAfterMs) !== null && _f !== void 0 ? _f : ((tries) => {
          return RECONNECT_INTERVALS[tries - 1] || DEFAULT_RECONNECT_FALLBACK;
        });
        let defaultEncode;
        let defaultDecode;
        const vsn = (_g = options === null || options === void 0 ? void 0 : options.vsn) !== null && _g !== void 0 ? _g : constants_1.DEFAULT_VSN;
        switch (vsn) {
          case constants_1.VSN_1_0_0:
            defaultEncode = (payload, callback) => {
              return callback(JSON.stringify(payload));
            };
            defaultDecode = (payload, callback) => {
              return callback(JSON.parse(payload));
            };
            break;
          case constants_1.VSN_2_0_0:
            defaultEncode = this.serializer.encode.bind(this.serializer);
            defaultDecode = this.serializer.decode.bind(this.serializer);
            break;
          default:
            throw new Error(`Unsupported serializer version: ${result.vsn}`);
        }
        result.vsn = vsn;
        result.encode = (_h = options === null || options === void 0 ? void 0 : options.encode) !== null && _h !== void 0 ? _h : defaultEncode;
        result.decode = (_j = options === null || options === void 0 ? void 0 : options.decode) !== null && _j !== void 0 ? _j : defaultDecode;
        result.beforeReconnect = this._reconnectAuth.bind(this);
        if ((options === null || options === void 0 ? void 0 : options.logLevel) || (options === null || options === void 0 ? void 0 : options.log_level)) {
          this.logLevel = options.logLevel || options.log_level;
          result.params = Object.assign(Object.assign({}, result.params), { log_level: this.logLevel });
        }
        if (this.worker) {
          if (typeof window !== "undefined" && !window.Worker) {
            throw new Error("Web Worker is not supported");
          }
          this.workerUrl = options === null || options === void 0 ? void 0 : options.workerUrl;
          result.autoSendHeartbeat = !this.worker;
        }
        return result;
      }
      /** @internal */
      async _reconnectAuth() {
        await this._waitForAuthIfNeeded();
        if (!this.isConnected()) {
          this.connect();
        }
      }
    };
    exports2.default = RealtimeClient2;
  }
});

// design/node_modules/@supabase/realtime-js/dist/main/index.js
var require_main2 = __commonJS({
  "design/node_modules/@supabase/realtime-js/dist/main/index.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.WebSocketFactory = exports2.REALTIME_CHANNEL_STATES = exports2.REALTIME_SUBSCRIBE_STATES = exports2.REALTIME_PRESENCE_LISTEN_EVENTS = exports2.REALTIME_POSTGRES_CHANGES_LISTEN_EVENT = exports2.REALTIME_LISTEN_TYPES = exports2.RealtimeClient = exports2.RealtimeChannel = exports2.RealtimePresence = void 0;
    var tslib_1 = (init_tslib_es6(), __toCommonJS(tslib_es6_exports));
    var RealtimeClient_1 = tslib_1.__importDefault(require_RealtimeClient());
    exports2.RealtimeClient = RealtimeClient_1.default;
    var RealtimeChannel_1 = tslib_1.__importStar(require_RealtimeChannel());
    exports2.RealtimeChannel = RealtimeChannel_1.default;
    Object.defineProperty(exports2, "REALTIME_LISTEN_TYPES", { enumerable: true, get: function() {
      return RealtimeChannel_1.REALTIME_LISTEN_TYPES;
    } });
    Object.defineProperty(exports2, "REALTIME_POSTGRES_CHANGES_LISTEN_EVENT", { enumerable: true, get: function() {
      return RealtimeChannel_1.REALTIME_POSTGRES_CHANGES_LISTEN_EVENT;
    } });
    Object.defineProperty(exports2, "REALTIME_SUBSCRIBE_STATES", { enumerable: true, get: function() {
      return RealtimeChannel_1.REALTIME_SUBSCRIBE_STATES;
    } });
    Object.defineProperty(exports2, "REALTIME_CHANNEL_STATES", { enumerable: true, get: function() {
      return RealtimeChannel_1.REALTIME_CHANNEL_STATES;
    } });
    var RealtimePresence_1 = tslib_1.__importStar(require_RealtimePresence());
    exports2.RealtimePresence = RealtimePresence_1.default;
    Object.defineProperty(exports2, "REALTIME_PRESENCE_LISTEN_EVENTS", { enumerable: true, get: function() {
      return RealtimePresence_1.REALTIME_PRESENCE_LISTEN_EVENTS;
    } });
    var websocket_factory_1 = tslib_1.__importDefault(require_websocket_factory());
    exports2.WebSocketFactory = websocket_factory_1.default;
  }
});

// design/node_modules/@supabase/auth-js/dist/main/lib/version.js
var require_version2 = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/lib/version.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.version = void 0;
    exports2.version = "2.104.1";
  }
});

// design/node_modules/@supabase/auth-js/dist/main/lib/constants.js
var require_constants2 = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/lib/constants.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.JWKS_TTL = exports2.BASE64URL_REGEX = exports2.API_VERSIONS = exports2.API_VERSION_HEADER_NAME = exports2.NETWORK_FAILURE = exports2.DEFAULT_HEADERS = exports2.AUDIENCE = exports2.STORAGE_KEY = exports2.GOTRUE_URL = exports2.EXPIRY_MARGIN_MS = exports2.AUTO_REFRESH_TICK_THRESHOLD = exports2.AUTO_REFRESH_TICK_DURATION_MS = void 0;
    var version_1 = require_version2();
    exports2.AUTO_REFRESH_TICK_DURATION_MS = 30 * 1e3;
    exports2.AUTO_REFRESH_TICK_THRESHOLD = 3;
    exports2.EXPIRY_MARGIN_MS = exports2.AUTO_REFRESH_TICK_THRESHOLD * exports2.AUTO_REFRESH_TICK_DURATION_MS;
    exports2.GOTRUE_URL = "http://localhost:9999";
    exports2.STORAGE_KEY = "supabase.auth.token";
    exports2.AUDIENCE = "";
    exports2.DEFAULT_HEADERS = { "X-Client-Info": `gotrue-js/${version_1.version}` };
    exports2.NETWORK_FAILURE = {
      MAX_RETRIES: 10,
      RETRY_INTERVAL: 2
      // in deciseconds
    };
    exports2.API_VERSION_HEADER_NAME = "X-Supabase-Api-Version";
    exports2.API_VERSIONS = {
      "2024-01-01": {
        timestamp: Date.parse("2024-01-01T00:00:00.0Z"),
        name: "2024-01-01"
      }
    };
    exports2.BASE64URL_REGEX = /^([a-z0-9_-]{4})*($|[a-z0-9_-]{3}$|[a-z0-9_-]{2}$)$/i;
    exports2.JWKS_TTL = 10 * 60 * 1e3;
  }
});

// design/node_modules/@supabase/auth-js/dist/main/lib/errors.js
var require_errors = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/lib/errors.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.AuthInvalidJwtError = exports2.AuthWeakPasswordError = exports2.AuthRetryableFetchError = exports2.AuthPKCECodeVerifierMissingError = exports2.AuthPKCEGrantCodeExchangeError = exports2.AuthImplicitGrantRedirectError = exports2.AuthInvalidCredentialsError = exports2.AuthInvalidTokenResponseError = exports2.AuthSessionMissingError = exports2.CustomAuthError = exports2.AuthUnknownError = exports2.AuthApiError = exports2.AuthError = void 0;
    exports2.isAuthError = isAuthError;
    exports2.isAuthApiError = isAuthApiError;
    exports2.isAuthSessionMissingError = isAuthSessionMissingError;
    exports2.isAuthImplicitGrantRedirectError = isAuthImplicitGrantRedirectError;
    exports2.isAuthPKCECodeVerifierMissingError = isAuthPKCECodeVerifierMissingError;
    exports2.isAuthRetryableFetchError = isAuthRetryableFetchError;
    exports2.isAuthWeakPasswordError = isAuthWeakPasswordError;
    var AuthError = class extends Error {
      constructor(message, status, code) {
        super(message);
        this.__isAuthError = true;
        this.name = "AuthError";
        this.status = status;
        this.code = code;
      }
      toJSON() {
        return {
          name: this.name,
          message: this.message,
          status: this.status,
          code: this.code
        };
      }
    };
    exports2.AuthError = AuthError;
    function isAuthError(error) {
      return typeof error === "object" && error !== null && "__isAuthError" in error;
    }
    var AuthApiError = class extends AuthError {
      constructor(message, status, code) {
        super(message, status, code);
        this.name = "AuthApiError";
        this.status = status;
        this.code = code;
      }
    };
    exports2.AuthApiError = AuthApiError;
    function isAuthApiError(error) {
      return isAuthError(error) && error.name === "AuthApiError";
    }
    var AuthUnknownError = class extends AuthError {
      constructor(message, originalError) {
        super(message);
        this.name = "AuthUnknownError";
        this.originalError = originalError;
      }
    };
    exports2.AuthUnknownError = AuthUnknownError;
    var CustomAuthError = class extends AuthError {
      constructor(message, name, status, code) {
        super(message, status, code);
        this.name = name;
        this.status = status;
      }
    };
    exports2.CustomAuthError = CustomAuthError;
    var AuthSessionMissingError = class extends CustomAuthError {
      constructor() {
        super("Auth session missing!", "AuthSessionMissingError", 400, void 0);
      }
    };
    exports2.AuthSessionMissingError = AuthSessionMissingError;
    function isAuthSessionMissingError(error) {
      return isAuthError(error) && error.name === "AuthSessionMissingError";
    }
    var AuthInvalidTokenResponseError = class extends CustomAuthError {
      constructor() {
        super("Auth session or user missing", "AuthInvalidTokenResponseError", 500, void 0);
      }
    };
    exports2.AuthInvalidTokenResponseError = AuthInvalidTokenResponseError;
    var AuthInvalidCredentialsError = class extends CustomAuthError {
      constructor(message) {
        super(message, "AuthInvalidCredentialsError", 400, void 0);
      }
    };
    exports2.AuthInvalidCredentialsError = AuthInvalidCredentialsError;
    var AuthImplicitGrantRedirectError = class extends CustomAuthError {
      constructor(message, details = null) {
        super(message, "AuthImplicitGrantRedirectError", 500, void 0);
        this.details = null;
        this.details = details;
      }
      toJSON() {
        return Object.assign(Object.assign({}, super.toJSON()), { details: this.details });
      }
    };
    exports2.AuthImplicitGrantRedirectError = AuthImplicitGrantRedirectError;
    function isAuthImplicitGrantRedirectError(error) {
      return isAuthError(error) && error.name === "AuthImplicitGrantRedirectError";
    }
    var AuthPKCEGrantCodeExchangeError = class extends CustomAuthError {
      constructor(message, details = null) {
        super(message, "AuthPKCEGrantCodeExchangeError", 500, void 0);
        this.details = null;
        this.details = details;
      }
      toJSON() {
        return Object.assign(Object.assign({}, super.toJSON()), { details: this.details });
      }
    };
    exports2.AuthPKCEGrantCodeExchangeError = AuthPKCEGrantCodeExchangeError;
    var AuthPKCECodeVerifierMissingError = class extends CustomAuthError {
      constructor() {
        super("PKCE code verifier not found in storage. This can happen if the auth flow was initiated in a different browser or device, or if the storage was cleared. For SSR frameworks (Next.js, SvelteKit, etc.), use @supabase/ssr on both the server and client to store the code verifier in cookies.", "AuthPKCECodeVerifierMissingError", 400, "pkce_code_verifier_not_found");
      }
    };
    exports2.AuthPKCECodeVerifierMissingError = AuthPKCECodeVerifierMissingError;
    function isAuthPKCECodeVerifierMissingError(error) {
      return isAuthError(error) && error.name === "AuthPKCECodeVerifierMissingError";
    }
    var AuthRetryableFetchError = class extends CustomAuthError {
      constructor(message, status) {
        super(message, "AuthRetryableFetchError", status, void 0);
      }
    };
    exports2.AuthRetryableFetchError = AuthRetryableFetchError;
    function isAuthRetryableFetchError(error) {
      return isAuthError(error) && error.name === "AuthRetryableFetchError";
    }
    var AuthWeakPasswordError = class extends CustomAuthError {
      constructor(message, status, reasons) {
        super(message, "AuthWeakPasswordError", status, "weak_password");
        this.reasons = reasons;
      }
      toJSON() {
        return Object.assign(Object.assign({}, super.toJSON()), { reasons: this.reasons });
      }
    };
    exports2.AuthWeakPasswordError = AuthWeakPasswordError;
    function isAuthWeakPasswordError(error) {
      return isAuthError(error) && error.name === "AuthWeakPasswordError";
    }
    var AuthInvalidJwtError = class extends CustomAuthError {
      constructor(message) {
        super(message, "AuthInvalidJwtError", 400, "invalid_jwt");
      }
    };
    exports2.AuthInvalidJwtError = AuthInvalidJwtError;
  }
});

// design/node_modules/@supabase/auth-js/dist/main/lib/base64url.js
var require_base64url = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/lib/base64url.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.byteToBase64URL = byteToBase64URL;
    exports2.byteFromBase64URL = byteFromBase64URL;
    exports2.stringToBase64URL = stringToBase64URL;
    exports2.stringFromBase64URL = stringFromBase64URL;
    exports2.codepointToUTF8 = codepointToUTF8;
    exports2.stringToUTF8 = stringToUTF8;
    exports2.stringFromUTF8 = stringFromUTF8;
    exports2.base64UrlToUint8Array = base64UrlToUint8Array;
    exports2.stringToUint8Array = stringToUint8Array;
    exports2.bytesToBase64URL = bytesToBase64URL;
    var TO_BASE64URL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_".split("");
    var IGNORE_BASE64URL = " 	\n\r=".split("");
    var FROM_BASE64URL = (() => {
      const charMap = new Array(128);
      for (let i = 0; i < charMap.length; i += 1) {
        charMap[i] = -1;
      }
      for (let i = 0; i < IGNORE_BASE64URL.length; i += 1) {
        charMap[IGNORE_BASE64URL[i].charCodeAt(0)] = -2;
      }
      for (let i = 0; i < TO_BASE64URL.length; i += 1) {
        charMap[TO_BASE64URL[i].charCodeAt(0)] = i;
      }
      return charMap;
    })();
    function byteToBase64URL(byte, state, emit) {
      if (byte !== null) {
        state.queue = state.queue << 8 | byte;
        state.queuedBits += 8;
        while (state.queuedBits >= 6) {
          const pos = state.queue >> state.queuedBits - 6 & 63;
          emit(TO_BASE64URL[pos]);
          state.queuedBits -= 6;
        }
      } else if (state.queuedBits > 0) {
        state.queue = state.queue << 6 - state.queuedBits;
        state.queuedBits = 6;
        while (state.queuedBits >= 6) {
          const pos = state.queue >> state.queuedBits - 6 & 63;
          emit(TO_BASE64URL[pos]);
          state.queuedBits -= 6;
        }
      }
    }
    function byteFromBase64URL(charCode, state, emit) {
      const bits = FROM_BASE64URL[charCode];
      if (bits > -1) {
        state.queue = state.queue << 6 | bits;
        state.queuedBits += 6;
        while (state.queuedBits >= 8) {
          emit(state.queue >> state.queuedBits - 8 & 255);
          state.queuedBits -= 8;
        }
      } else if (bits === -2) {
        return;
      } else {
        throw new Error(`Invalid Base64-URL character "${String.fromCharCode(charCode)}"`);
      }
    }
    function stringToBase64URL(str) {
      const base64 = [];
      const emitter = (char) => {
        base64.push(char);
      };
      const state = { queue: 0, queuedBits: 0 };
      stringToUTF8(str, (byte) => {
        byteToBase64URL(byte, state, emitter);
      });
      byteToBase64URL(null, state, emitter);
      return base64.join("");
    }
    function stringFromBase64URL(str) {
      const conv = [];
      const utf8Emit = (codepoint) => {
        conv.push(String.fromCodePoint(codepoint));
      };
      const utf8State = {
        utf8seq: 0,
        codepoint: 0
      };
      const b64State = { queue: 0, queuedBits: 0 };
      const byteEmit = (byte) => {
        stringFromUTF8(byte, utf8State, utf8Emit);
      };
      for (let i = 0; i < str.length; i += 1) {
        byteFromBase64URL(str.charCodeAt(i), b64State, byteEmit);
      }
      return conv.join("");
    }
    function codepointToUTF8(codepoint, emit) {
      if (codepoint <= 127) {
        emit(codepoint);
        return;
      } else if (codepoint <= 2047) {
        emit(192 | codepoint >> 6);
        emit(128 | codepoint & 63);
        return;
      } else if (codepoint <= 65535) {
        emit(224 | codepoint >> 12);
        emit(128 | codepoint >> 6 & 63);
        emit(128 | codepoint & 63);
        return;
      } else if (codepoint <= 1114111) {
        emit(240 | codepoint >> 18);
        emit(128 | codepoint >> 12 & 63);
        emit(128 | codepoint >> 6 & 63);
        emit(128 | codepoint & 63);
        return;
      }
      throw new Error(`Unrecognized Unicode codepoint: ${codepoint.toString(16)}`);
    }
    function stringToUTF8(str, emit) {
      for (let i = 0; i < str.length; i += 1) {
        let codepoint = str.charCodeAt(i);
        if (codepoint > 55295 && codepoint <= 56319) {
          const highSurrogate = (codepoint - 55296) * 1024 & 65535;
          const lowSurrogate = str.charCodeAt(i + 1) - 56320 & 65535;
          codepoint = (lowSurrogate | highSurrogate) + 65536;
          i += 1;
        }
        codepointToUTF8(codepoint, emit);
      }
    }
    function stringFromUTF8(byte, state, emit) {
      if (state.utf8seq === 0) {
        if (byte <= 127) {
          emit(byte);
          return;
        }
        for (let leadingBit = 1; leadingBit < 6; leadingBit += 1) {
          if ((byte >> 7 - leadingBit & 1) === 0) {
            state.utf8seq = leadingBit;
            break;
          }
        }
        if (state.utf8seq === 2) {
          state.codepoint = byte & 31;
        } else if (state.utf8seq === 3) {
          state.codepoint = byte & 15;
        } else if (state.utf8seq === 4) {
          state.codepoint = byte & 7;
        } else {
          throw new Error("Invalid UTF-8 sequence");
        }
        state.utf8seq -= 1;
      } else if (state.utf8seq > 0) {
        if (byte <= 127) {
          throw new Error("Invalid UTF-8 sequence");
        }
        state.codepoint = state.codepoint << 6 | byte & 63;
        state.utf8seq -= 1;
        if (state.utf8seq === 0) {
          emit(state.codepoint);
        }
      }
    }
    function base64UrlToUint8Array(str) {
      const result = [];
      const state = { queue: 0, queuedBits: 0 };
      const onByte = (byte) => {
        result.push(byte);
      };
      for (let i = 0; i < str.length; i += 1) {
        byteFromBase64URL(str.charCodeAt(i), state, onByte);
      }
      return new Uint8Array(result);
    }
    function stringToUint8Array(str) {
      const result = [];
      stringToUTF8(str, (byte) => result.push(byte));
      return new Uint8Array(result);
    }
    function bytesToBase64URL(bytes) {
      const result = [];
      const state = { queue: 0, queuedBits: 0 };
      const onChar = (char) => {
        result.push(char);
      };
      bytes.forEach((byte) => byteToBase64URL(byte, state, onChar));
      byteToBase64URL(null, state, onChar);
      return result.join("");
    }
  }
});

// design/node_modules/@supabase/auth-js/dist/main/lib/helpers.js
var require_helpers = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/lib/helpers.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.Deferred = exports2.removeItemAsync = exports2.getItemAsync = exports2.setItemAsync = exports2.looksLikeFetchResponse = exports2.resolveFetch = exports2.supportsLocalStorage = exports2.isBrowser = void 0;
    exports2.expiresAt = expiresAt;
    exports2.generateCallbackId = generateCallbackId;
    exports2.parseParametersFromURL = parseParametersFromURL;
    exports2.decodeJWT = decodeJWT;
    exports2.sleep = sleep2;
    exports2.retryable = retryable;
    exports2.generatePKCEVerifier = generatePKCEVerifier;
    exports2.generatePKCEChallenge = generatePKCEChallenge;
    exports2.getCodeChallengeAndMethod = getCodeChallengeAndMethod;
    exports2.parseResponseAPIVersion = parseResponseAPIVersion;
    exports2.validateExp = validateExp;
    exports2.getAlgorithm = getAlgorithm;
    exports2.validateUUID = validateUUID;
    exports2.userNotAvailableProxy = userNotAvailableProxy;
    exports2.insecureUserWarningProxy = insecureUserWarningProxy;
    exports2.deepClone = deepClone;
    var constants_1 = require_constants2();
    var errors_1 = require_errors();
    var base64url_1 = require_base64url();
    function expiresAt(expiresIn) {
      const timeNow = Math.round(Date.now() / 1e3);
      return timeNow + expiresIn;
    }
    function generateCallbackId() {
      return /* @__PURE__ */ Symbol("auth-callback");
    }
    var isBrowser = () => typeof window !== "undefined" && typeof document !== "undefined";
    exports2.isBrowser = isBrowser;
    var localStorageWriteTests = {
      tested: false,
      writable: false
    };
    var supportsLocalStorage = () => {
      if (!(0, exports2.isBrowser)()) {
        return false;
      }
      try {
        if (typeof globalThis.localStorage !== "object") {
          return false;
        }
      } catch (e) {
        return false;
      }
      if (localStorageWriteTests.tested) {
        return localStorageWriteTests.writable;
      }
      const randomKey = `lswt-${Math.random()}${Math.random()}`;
      try {
        globalThis.localStorage.setItem(randomKey, randomKey);
        globalThis.localStorage.removeItem(randomKey);
        localStorageWriteTests.tested = true;
        localStorageWriteTests.writable = true;
      } catch (e) {
        localStorageWriteTests.tested = true;
        localStorageWriteTests.writable = false;
      }
      return localStorageWriteTests.writable;
    };
    exports2.supportsLocalStorage = supportsLocalStorage;
    function parseParametersFromURL(href) {
      const result = {};
      const url = new URL(href);
      if (url.hash && url.hash[0] === "#") {
        try {
          const hashSearchParams = new URLSearchParams(url.hash.substring(1));
          hashSearchParams.forEach((value, key) => {
            result[key] = value;
          });
        } catch (e) {
        }
      }
      url.searchParams.forEach((value, key) => {
        result[key] = value;
      });
      return result;
    }
    var resolveFetch3 = (customFetch) => {
      if (customFetch) {
        return (...args) => customFetch(...args);
      }
      return (...args) => fetch(...args);
    };
    exports2.resolveFetch = resolveFetch3;
    var looksLikeFetchResponse = (maybeResponse) => {
      return typeof maybeResponse === "object" && maybeResponse !== null && "status" in maybeResponse && "ok" in maybeResponse && "json" in maybeResponse && typeof maybeResponse.json === "function";
    };
    exports2.looksLikeFetchResponse = looksLikeFetchResponse;
    var setItemAsync = async (storage, key, data) => {
      await storage.setItem(key, JSON.stringify(data));
    };
    exports2.setItemAsync = setItemAsync;
    var getItemAsync = async (storage, key) => {
      const value = await storage.getItem(key);
      if (!value) {
        return null;
      }
      try {
        return JSON.parse(value);
      } catch (_a) {
        return value;
      }
    };
    exports2.getItemAsync = getItemAsync;
    var removeItemAsync = async (storage, key) => {
      await storage.removeItem(key);
    };
    exports2.removeItemAsync = removeItemAsync;
    var Deferred = class _Deferred {
      constructor() {
        ;
        this.promise = new _Deferred.promiseConstructor((res, rej) => {
          ;
          this.resolve = res;
          this.reject = rej;
        });
      }
    };
    exports2.Deferred = Deferred;
    Deferred.promiseConstructor = Promise;
    function decodeJWT(token) {
      const parts = token.split(".");
      if (parts.length !== 3) {
        throw new errors_1.AuthInvalidJwtError("Invalid JWT structure");
      }
      for (let i = 0; i < parts.length; i++) {
        if (!constants_1.BASE64URL_REGEX.test(parts[i])) {
          throw new errors_1.AuthInvalidJwtError("JWT not in base64url format");
        }
      }
      const data = {
        // using base64url lib
        header: JSON.parse((0, base64url_1.stringFromBase64URL)(parts[0])),
        payload: JSON.parse((0, base64url_1.stringFromBase64URL)(parts[1])),
        signature: (0, base64url_1.base64UrlToUint8Array)(parts[2]),
        raw: {
          header: parts[0],
          payload: parts[1]
        }
      };
      return data;
    }
    async function sleep2(time) {
      return await new Promise((accept) => {
        setTimeout(() => accept(null), time);
      });
    }
    function retryable(fn, isRetryable) {
      const promise = new Promise((accept, reject) => {
        ;
        (async () => {
          for (let attempt = 0; attempt < Infinity; attempt++) {
            try {
              const result = await fn(attempt);
              if (!isRetryable(attempt, null, result)) {
                accept(result);
                return;
              }
            } catch (e) {
              if (!isRetryable(attempt, e)) {
                reject(e);
                return;
              }
            }
          }
        })();
      });
      return promise;
    }
    function dec2hex(dec) {
      return ("0" + dec.toString(16)).substr(-2);
    }
    function generatePKCEVerifier() {
      const verifierLength = 56;
      const array = new Uint32Array(verifierLength);
      if (typeof crypto === "undefined") {
        const charSet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
        const charSetLen = charSet.length;
        let verifier = "";
        for (let i = 0; i < verifierLength; i++) {
          verifier += charSet.charAt(Math.floor(Math.random() * charSetLen));
        }
        return verifier;
      }
      crypto.getRandomValues(array);
      return Array.from(array, dec2hex).join("");
    }
    async function sha256(randomString) {
      const encoder = new TextEncoder();
      const encodedData = encoder.encode(randomString);
      const hash = await crypto.subtle.digest("SHA-256", encodedData);
      const bytes = new Uint8Array(hash);
      return Array.from(bytes).map((c) => String.fromCharCode(c)).join("");
    }
    async function generatePKCEChallenge(verifier) {
      const hasCryptoSupport = typeof crypto !== "undefined" && typeof crypto.subtle !== "undefined" && typeof TextEncoder !== "undefined";
      if (!hasCryptoSupport) {
        console.warn("WebCrypto API is not supported. Code challenge method will default to use plain instead of sha256.");
        return verifier;
      }
      const hashed = await sha256(verifier);
      return btoa(hashed).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    }
    async function getCodeChallengeAndMethod(storage, storageKey, isPasswordRecovery = false) {
      const codeVerifier = generatePKCEVerifier();
      let storedCodeVerifier = codeVerifier;
      if (isPasswordRecovery) {
        storedCodeVerifier += "/recovery";
      }
      await (0, exports2.setItemAsync)(storage, `${storageKey}-code-verifier`, storedCodeVerifier);
      const codeChallenge = await generatePKCEChallenge(codeVerifier);
      const codeChallengeMethod = codeVerifier === codeChallenge ? "plain" : "s256";
      return [codeChallenge, codeChallengeMethod];
    }
    var API_VERSION_REGEX = /^2[0-9]{3}-(0[1-9]|1[0-2])-(0[1-9]|1[0-9]|2[0-9]|3[0-1])$/i;
    function parseResponseAPIVersion(response2) {
      const apiVersion = response2.headers.get(constants_1.API_VERSION_HEADER_NAME);
      if (!apiVersion) {
        return null;
      }
      if (!apiVersion.match(API_VERSION_REGEX)) {
        return null;
      }
      try {
        const date = /* @__PURE__ */ new Date(`${apiVersion}T00:00:00.0Z`);
        return date;
      } catch (e) {
        return null;
      }
    }
    function validateExp(exp) {
      if (!exp) {
        throw new Error("Missing exp claim");
      }
      const timeNow = Math.floor(Date.now() / 1e3);
      if (exp <= timeNow) {
        throw new Error("JWT has expired");
      }
    }
    function getAlgorithm(alg) {
      switch (alg) {
        case "RS256":
          return {
            name: "RSASSA-PKCS1-v1_5",
            hash: { name: "SHA-256" }
          };
        case "ES256":
          return {
            name: "ECDSA",
            namedCurve: "P-256",
            hash: { name: "SHA-256" }
          };
        default:
          throw new Error("Invalid alg claim");
      }
    }
    var UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
    function validateUUID(str) {
      if (!UUID_REGEX.test(str)) {
        throw new Error("@supabase/auth-js: Expected parameter to be UUID but is not");
      }
    }
    function userNotAvailableProxy() {
      const proxyTarget = {};
      return new Proxy(proxyTarget, {
        get: (target, prop) => {
          if (prop === "__isUserNotAvailableProxy") {
            return true;
          }
          if (typeof prop === "symbol") {
            const sProp = prop.toString();
            if (sProp === "Symbol(Symbol.toPrimitive)" || sProp === "Symbol(Symbol.toStringTag)" || sProp === "Symbol(util.inspect.custom)") {
              return void 0;
            }
          }
          throw new Error(`@supabase/auth-js: client was created with userStorage option and there was no user stored in the user storage. Accessing the "${prop}" property of the session object is not supported. Please use getUser() instead.`);
        },
        set: (_target, prop) => {
          throw new Error(`@supabase/auth-js: client was created with userStorage option and there was no user stored in the user storage. Setting the "${prop}" property of the session object is not supported. Please use getUser() to fetch a user object you can manipulate.`);
        },
        deleteProperty: (_target, prop) => {
          throw new Error(`@supabase/auth-js: client was created with userStorage option and there was no user stored in the user storage. Deleting the "${prop}" property of the session object is not supported. Please use getUser() to fetch a user object you can manipulate.`);
        }
      });
    }
    function insecureUserWarningProxy(user, suppressWarningRef) {
      return new Proxy(user, {
        get: (target, prop, receiver) => {
          if (prop === "__isInsecureUserWarningProxy") {
            return true;
          }
          if (typeof prop === "symbol") {
            const sProp = prop.toString();
            if (sProp === "Symbol(Symbol.toPrimitive)" || sProp === "Symbol(Symbol.toStringTag)" || sProp === "Symbol(util.inspect.custom)" || sProp === "Symbol(nodejs.util.inspect.custom)") {
              return Reflect.get(target, prop, receiver);
            }
          }
          if (!suppressWarningRef.value && typeof prop === "string") {
            console.warn("Using the user object as returned from supabase.auth.getSession() or from some supabase.auth.onAuthStateChange() events could be insecure! This value comes directly from the storage medium (usually cookies on the server) and may not be authentic. Use supabase.auth.getUser() instead which authenticates the data by contacting the Supabase Auth server.");
            suppressWarningRef.value = true;
          }
          return Reflect.get(target, prop, receiver);
        }
      });
    }
    function deepClone(obj) {
      return JSON.parse(JSON.stringify(obj));
    }
  }
});

// design/node_modules/@supabase/auth-js/dist/main/lib/fetch.js
var require_fetch = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/lib/fetch.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.handleError = handleError2;
    exports2._request = _request;
    exports2._sessionResponse = _sessionResponse;
    exports2._sessionResponsePassword = _sessionResponsePassword;
    exports2._userResponse = _userResponse;
    exports2._ssoResponse = _ssoResponse;
    exports2._generateLinkResponse = _generateLinkResponse;
    exports2._noResolveJsonResponse = _noResolveJsonResponse;
    var tslib_1 = (init_tslib_es6(), __toCommonJS(tslib_es6_exports));
    var constants_1 = require_constants2();
    var helpers_1 = require_helpers();
    var errors_1 = require_errors();
    var _getErrorMessage2 = (err) => err.msg || err.message || err.error_description || err.error || JSON.stringify(err);
    var NETWORK_ERROR_CODES = [502, 503, 504, 520, 521, 522, 523, 524, 530];
    async function handleError2(error) {
      var _a;
      if (!(0, helpers_1.looksLikeFetchResponse)(error)) {
        throw new errors_1.AuthRetryableFetchError(_getErrorMessage2(error), 0);
      }
      if (NETWORK_ERROR_CODES.includes(error.status)) {
        throw new errors_1.AuthRetryableFetchError(_getErrorMessage2(error), error.status);
      }
      let data;
      try {
        data = await error.json();
      } catch (e) {
        throw new errors_1.AuthUnknownError(_getErrorMessage2(e), e);
      }
      let errorCode = void 0;
      const responseAPIVersion = (0, helpers_1.parseResponseAPIVersion)(error);
      if (responseAPIVersion && responseAPIVersion.getTime() >= constants_1.API_VERSIONS["2024-01-01"].timestamp && typeof data === "object" && data && typeof data.code === "string") {
        errorCode = data.code;
      } else if (typeof data === "object" && data && typeof data.error_code === "string") {
        errorCode = data.error_code;
      }
      if (!errorCode) {
        if (typeof data === "object" && data && typeof data.weak_password === "object" && data.weak_password && Array.isArray(data.weak_password.reasons) && data.weak_password.reasons.length && data.weak_password.reasons.reduce((a, i) => a && typeof i === "string", true)) {
          throw new errors_1.AuthWeakPasswordError(_getErrorMessage2(data), error.status, data.weak_password.reasons);
        }
      } else if (errorCode === "weak_password") {
        throw new errors_1.AuthWeakPasswordError(_getErrorMessage2(data), error.status, ((_a = data.weak_password) === null || _a === void 0 ? void 0 : _a.reasons) || []);
      } else if (errorCode === "session_not_found") {
        throw new errors_1.AuthSessionMissingError();
      }
      throw new errors_1.AuthApiError(_getErrorMessage2(data), error.status || 500, errorCode);
    }
    var _getRequestParams2 = (method, options, parameters, body) => {
      const params = { method, headers: (options === null || options === void 0 ? void 0 : options.headers) || {} };
      if (method === "GET") {
        return params;
      }
      params.headers = Object.assign({ "Content-Type": "application/json;charset=UTF-8" }, options === null || options === void 0 ? void 0 : options.headers);
      params.body = JSON.stringify(body);
      return Object.assign(Object.assign({}, params), parameters);
    };
    async function _request(fetcher, method, url, options) {
      var _a;
      const headers = Object.assign({}, options === null || options === void 0 ? void 0 : options.headers);
      if (!headers[constants_1.API_VERSION_HEADER_NAME]) {
        headers[constants_1.API_VERSION_HEADER_NAME] = constants_1.API_VERSIONS["2024-01-01"].name;
      }
      if (options === null || options === void 0 ? void 0 : options.jwt) {
        headers["Authorization"] = `Bearer ${options.jwt}`;
      }
      const qs = (_a = options === null || options === void 0 ? void 0 : options.query) !== null && _a !== void 0 ? _a : {};
      if (options === null || options === void 0 ? void 0 : options.redirectTo) {
        qs["redirect_to"] = options.redirectTo;
      }
      const queryString = Object.keys(qs).length ? "?" + new URLSearchParams(qs).toString() : "";
      const data = await _handleRequest2(fetcher, method, url + queryString, {
        headers,
        noResolveJson: options === null || options === void 0 ? void 0 : options.noResolveJson
      }, {}, options === null || options === void 0 ? void 0 : options.body);
      return (options === null || options === void 0 ? void 0 : options.xform) ? options === null || options === void 0 ? void 0 : options.xform(data) : { data: Object.assign({}, data), error: null };
    }
    async function _handleRequest2(fetcher, method, url, options, parameters, body) {
      const requestParams = _getRequestParams2(method, options, parameters, body);
      let result;
      try {
        result = await fetcher(url, Object.assign({}, requestParams));
      } catch (e) {
        console.error(e);
        throw new errors_1.AuthRetryableFetchError(_getErrorMessage2(e), 0);
      }
      if (!result.ok) {
        await handleError2(result);
      }
      if (options === null || options === void 0 ? void 0 : options.noResolveJson) {
        return result;
      }
      try {
        return await result.json();
      } catch (e) {
        await handleError2(e);
      }
    }
    function _sessionResponse(data) {
      var _a;
      let session = null;
      if (hasSession(data)) {
        session = Object.assign({}, data);
        if (!data.expires_at) {
          session.expires_at = (0, helpers_1.expiresAt)(data.expires_in);
        }
      }
      const user = (_a = data.user) !== null && _a !== void 0 ? _a : data;
      return { data: { session, user }, error: null };
    }
    function _sessionResponsePassword(data) {
      const response2 = _sessionResponse(data);
      if (!response2.error && data.weak_password && typeof data.weak_password === "object" && Array.isArray(data.weak_password.reasons) && data.weak_password.reasons.length && data.weak_password.message && typeof data.weak_password.message === "string" && data.weak_password.reasons.reduce((a, i) => a && typeof i === "string", true)) {
        response2.data.weak_password = data.weak_password;
      }
      return response2;
    }
    function _userResponse(data) {
      var _a;
      const user = (_a = data.user) !== null && _a !== void 0 ? _a : data;
      return { data: { user }, error: null };
    }
    function _ssoResponse(data) {
      return { data, error: null };
    }
    function _generateLinkResponse(data) {
      const { action_link, email_otp, hashed_token, redirect_to, verification_type } = data, rest = tslib_1.__rest(data, ["action_link", "email_otp", "hashed_token", "redirect_to", "verification_type"]);
      const properties = {
        action_link,
        email_otp,
        hashed_token,
        redirect_to,
        verification_type
      };
      const user = Object.assign({}, rest);
      return {
        data: {
          properties,
          user
        },
        error: null
      };
    }
    function _noResolveJsonResponse(data) {
      return data;
    }
    function hasSession(data) {
      return data.access_token && data.refresh_token && data.expires_in;
    }
  }
});

// design/node_modules/@supabase/auth-js/dist/main/lib/types.js
var require_types2 = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/lib/types.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.SIGN_OUT_SCOPES = void 0;
    exports2.SIGN_OUT_SCOPES = ["global", "local", "others"];
  }
});

// design/node_modules/@supabase/auth-js/dist/main/GoTrueAdminApi.js
var require_GoTrueAdminApi = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/GoTrueAdminApi.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    var tslib_1 = (init_tslib_es6(), __toCommonJS(tslib_es6_exports));
    var fetch_1 = require_fetch();
    var helpers_1 = require_helpers();
    var types_1 = require_types2();
    var errors_1 = require_errors();
    var GoTrueAdminApi = class {
      /**
       * Creates an admin API client that can be used to manage users and OAuth clients.
       *
       * @example Using supabase-js (recommended)
       * ```ts
       * import { createClient } from '@supabase/supabase-js'
       *
       * const supabase = createClient('https://xyzcompany.supabase.co', 'secret-or-service-role-key')
       * const { data, error } = await supabase.auth.admin.listUsers()
       * ```
       *
       * @example Standalone import for bundle-sensitive environments
       * ```ts
       * import { GoTrueAdminApi } from '@supabase/auth-js'
       *
       * const admin = new GoTrueAdminApi({
       *   url: 'https://xyzcompany.supabase.co/auth/v1',
       *   headers: { Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}` },
       * })
       * ```
       */
      constructor({ url = "", headers = {}, fetch: fetch2 }) {
        this.url = url;
        this.headers = headers;
        this.fetch = (0, helpers_1.resolveFetch)(fetch2);
        this.mfa = {
          listFactors: this._listFactors.bind(this),
          deleteFactor: this._deleteFactor.bind(this)
        };
        this.oauth = {
          listClients: this._listOAuthClients.bind(this),
          createClient: this._createOAuthClient.bind(this),
          getClient: this._getOAuthClient.bind(this),
          updateClient: this._updateOAuthClient.bind(this),
          deleteClient: this._deleteOAuthClient.bind(this),
          regenerateClientSecret: this._regenerateOAuthClientSecret.bind(this)
        };
        this.customProviders = {
          listProviders: this._listCustomProviders.bind(this),
          createProvider: this._createCustomProvider.bind(this),
          getProvider: this._getCustomProvider.bind(this),
          updateProvider: this._updateCustomProvider.bind(this),
          deleteProvider: this._deleteCustomProvider.bind(this)
        };
      }
      /**
       * Removes a logged-in session.
       * @param jwt A valid, logged-in JWT.
       * @param scope The logout sope.
       *
       * @category Auth
       */
      async signOut(jwt, scope = types_1.SIGN_OUT_SCOPES[0]) {
        if (types_1.SIGN_OUT_SCOPES.indexOf(scope) < 0) {
          throw new Error(`@supabase/auth-js: Parameter scope must be one of ${types_1.SIGN_OUT_SCOPES.join(", ")}`);
        }
        try {
          await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/logout?scope=${scope}`, {
            headers: this.headers,
            jwt,
            noResolveJson: true
          });
          return { data: null, error: null };
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          throw error;
        }
      }
      /**
       * Sends an invite link to an email address.
       * @param email The email address of the user.
       * @param options Additional options to be included when inviting.
       *
       * @category Auth
       *
       * @remarks
       * - Sends an invite link to the user's email address.
       * - The `inviteUserByEmail()` method is typically used by administrators to invite users to join the application.
       * - Note that PKCE is not supported when using `inviteUserByEmail`. This is because the browser initiating the invite is often different from the browser accepting the invite which makes it difficult to provide the security guarantees required of the PKCE flow.
       *
       * @example Invite a user
       * ```js
       * const { data, error } = await supabase.auth.admin.inviteUserByEmail('email@example.com')
       * ```
       *
       * @exampleResponse Invite a user
       * ```json
       * {
       *   "data": {
       *     "user": {
       *       "id": "11111111-1111-1111-1111-111111111111",
       *       "aud": "authenticated",
       *       "role": "authenticated",
       *       "email": "example@email.com",
       *       "invited_at": "2024-01-01T00:00:00Z",
       *       "phone": "",
       *       "confirmation_sent_at": "2024-01-01T00:00:00Z",
       *       "app_metadata": {
       *         "provider": "email",
       *         "providers": [
       *           "email"
       *         ]
       *       },
       *       "user_metadata": {},
       *       "identities": [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "id": "11111111-1111-1111-1111-111111111111",
       *           "user_id": "11111111-1111-1111-1111-111111111111",
       *           "identity_data": {
       *             "email": "example@email.com",
       *             "email_verified": false,
       *             "phone_verified": false,
       *             "sub": "11111111-1111-1111-1111-111111111111"
       *           },
       *           "provider": "email",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "example@email.com"
       *         }
       *       ],
       *       "created_at": "2024-01-01T00:00:00Z",
       *       "updated_at": "2024-01-01T00:00:00Z",
       *       "is_anonymous": false
       *     }
       *   },
       *   "error": null
       * }
       * ```
       */
      async inviteUserByEmail(email, options = {}) {
        try {
          return await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/invite`, {
            body: { email, data: options.data },
            headers: this.headers,
            redirectTo: options.redirectTo,
            xform: fetch_1._userResponse
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: { user: null }, error };
          }
          throw error;
        }
      }
      /**
       * Generates email links and OTPs to be sent via a custom email provider.
       * @param email The user's email.
       * @param options.password User password. For signup only.
       * @param options.data Optional user metadata. For signup only.
       * @param options.redirectTo The redirect url which should be appended to the generated link
       *
       * @category Auth
       *
       * @remarks
       * - The following types can be passed into `generateLink()`: `signup`, `magiclink`, `invite`, `recovery`, `email_change_current`, `email_change_new`, `phone_change`.
       * - `generateLink()` only generates the email link for `email_change_email` if the **Secure email change** is enabled in your project's [email auth provider settings](/dashboard/project/_/auth/providers).
       * - `generateLink()` handles the creation of the user for `signup`, `invite` and `magiclink`.
       *
       * @example Generate a signup link
       * ```js
       * const { data, error } = await supabase.auth.admin.generateLink({
       *   type: 'signup',
       *   email: 'email@example.com',
       *   password: 'secret'
       * })
       * ```
       *
       * @exampleResponse Generate a signup link
       * ```json
       * {
       *   "data": {
       *     "properties": {
       *       "action_link": "<LINK_TO_SEND_TO_USER>",
       *       "email_otp": "999999",
       *       "hashed_token": "<HASHED_TOKEN",
       *       "redirect_to": "<REDIRECT_URL>",
       *       "verification_type": "signup"
       *     },
       *     "user": {
       *       "id": "11111111-1111-1111-1111-111111111111",
       *       "aud": "authenticated",
       *       "role": "authenticated",
       *       "email": "email@example.com",
       *       "phone": "",
       *       "confirmation_sent_at": "2024-01-01T00:00:00Z",
       *       "app_metadata": {
       *         "provider": "email",
       *         "providers": [
       *           "email"
       *         ]
       *       },
       *       "user_metadata": {},
       *       "identities": [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "id": "11111111-1111-1111-1111-111111111111",
       *           "user_id": "11111111-1111-1111-1111-111111111111",
       *           "identity_data": {
       *             "email": "email@example.com",
       *             "email_verified": false,
       *             "phone_verified": false,
       *             "sub": "11111111-1111-1111-1111-111111111111"
       *           },
       *           "provider": "email",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "email@example.com"
       *         }
       *       ],
       *       "created_at": "2024-01-01T00:00:00Z",
       *       "updated_at": "2024-01-01T00:00:00Z",
       *       "is_anonymous": false
       *     }
       *   },
       *   "error": null
       * }
       * ```
       *
       * @example Generate an invite link
       * ```js
       * const { data, error } = await supabase.auth.admin.generateLink({
       *   type: 'invite',
       *   email: 'email@example.com'
       * })
       * ```
       *
       * @example Generate a magic link
       * ```js
       * const { data, error } = await supabase.auth.admin.generateLink({
       *   type: 'magiclink',
       *   email: 'email@example.com'
       * })
       * ```
       *
       * @example Generate a recovery link
       * ```js
       * const { data, error } = await supabase.auth.admin.generateLink({
       *   type: 'recovery',
       *   email: 'email@example.com'
       * })
       * ```
       *
       * @example Generate links to change current email address
       * ```js
       * // generate an email change link to be sent to the current email address
       * const { data, error } = await supabase.auth.admin.generateLink({
       *   type: 'email_change_current',
       *   email: 'current.email@example.com',
       *   newEmail: 'new.email@example.com'
       * })
       *
       * // generate an email change link to be sent to the new email address
       * const { data, error } = await supabase.auth.admin.generateLink({
       *   type: 'email_change_new',
       *   email: 'current.email@example.com',
       *   newEmail: 'new.email@example.com'
       * })
       * ```
       */
      async generateLink(params) {
        try {
          const { options } = params, rest = tslib_1.__rest(params, ["options"]);
          const body = Object.assign(Object.assign({}, rest), options);
          if ("newEmail" in rest) {
            body.new_email = rest === null || rest === void 0 ? void 0 : rest.newEmail;
            delete body["newEmail"];
          }
          return await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/admin/generate_link`, {
            body,
            headers: this.headers,
            xform: fetch_1._generateLinkResponse,
            redirectTo: options === null || options === void 0 ? void 0 : options.redirectTo
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return {
              data: {
                properties: null,
                user: null
              },
              error
            };
          }
          throw error;
        }
      }
      // User Admin API
      /**
       * Creates a new user.
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       *
       * @category Auth
       *
       * @remarks
       * - To confirm the user's email address or phone number, set `email_confirm` or `phone_confirm` to true. Both arguments default to false.
       * - `createUser()` will not send a confirmation email to the user. You can use [`inviteUserByEmail()`](/docs/reference/javascript/auth-admin-inviteuserbyemail) if you want to send them an email invite instead.
       * - If you are sure that the created user's email or phone number is legitimate and verified, you can set the `email_confirm` or `phone_confirm` param to `true`.
       *
       * @example With custom user metadata
       * ```js
       * const { data, error } = await supabase.auth.admin.createUser({
       *   email: 'user@email.com',
       *   password: 'password',
       *   user_metadata: { name: 'Yoda' }
       * })
       * ```
       *
       * @exampleResponse With custom user metadata
       * ```json
       * {
       *   data: {
       *     user: {
       *       id: '1',
       *       aud: 'authenticated',
       *       role: 'authenticated',
       *       email: 'example@email.com',
       *       email_confirmed_at: '2024-01-01T00:00:00Z',
       *       phone: '',
       *       confirmation_sent_at: '2024-01-01T00:00:00Z',
       *       confirmed_at: '2024-01-01T00:00:00Z',
       *       last_sign_in_at: '2024-01-01T00:00:00Z',
       *       app_metadata: {},
       *       user_metadata: {},
       *       identities: [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "id": "1",
       *           "user_id": "1",
       *           "identity_data": {
       *             "email": "example@email.com",
       *             "email_verified": true,
       *             "phone_verified": false,
       *             "sub": "1"
       *           },
       *           "provider": "email",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "email@example.com"
       *         },
       *       ],
       *       created_at: '2024-01-01T00:00:00Z',
       *       updated_at: '2024-01-01T00:00:00Z',
       *       is_anonymous: false,
       *     }
       *   }
       *   error: null
       * }
       * ```
       *
       * @example Auto-confirm the user's email
       * ```js
       * const { data, error } = await supabase.auth.admin.createUser({
       *   email: 'user@email.com',
       *   email_confirm: true
       * })
       * ```
       *
       * @example Auto-confirm the user's phone number
       * ```js
       * const { data, error } = await supabase.auth.admin.createUser({
       *   phone: '1234567890',
       *   phone_confirm: true
       * })
       * ```
       */
      async createUser(attributes) {
        try {
          return await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/admin/users`, {
            body: attributes,
            headers: this.headers,
            xform: fetch_1._userResponse
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: { user: null }, error };
          }
          throw error;
        }
      }
      /**
       * Get a list of users.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       * @param params An object which supports `page` and `perPage` as numbers, to alter the paginated results.
       *
       * @category Auth
       *
       * @remarks
       * - Defaults to return 50 users per page.
       *
       * @example Get a page of users
       * ```js
       * const { data: { users }, error } = await supabase.auth.admin.listUsers()
       * ```
       *
       * @example Paginated list of users
       * ```js
       * const { data: { users }, error } = await supabase.auth.admin.listUsers({
       *   page: 1,
       *   perPage: 1000
       * })
       * ```
       */
      async listUsers(params) {
        var _a, _b, _c, _d, _e, _f, _g;
        try {
          const pagination = { nextPage: null, lastPage: 0, total: 0 };
          const response2 = await (0, fetch_1._request)(this.fetch, "GET", `${this.url}/admin/users`, {
            headers: this.headers,
            noResolveJson: true,
            query: {
              page: (_b = (_a = params === null || params === void 0 ? void 0 : params.page) === null || _a === void 0 ? void 0 : _a.toString()) !== null && _b !== void 0 ? _b : "",
              per_page: (_d = (_c = params === null || params === void 0 ? void 0 : params.perPage) === null || _c === void 0 ? void 0 : _c.toString()) !== null && _d !== void 0 ? _d : ""
            },
            xform: fetch_1._noResolveJsonResponse
          });
          if (response2.error)
            throw response2.error;
          const users = await response2.json();
          const total = (_e = response2.headers.get("x-total-count")) !== null && _e !== void 0 ? _e : 0;
          const links = (_g = (_f = response2.headers.get("link")) === null || _f === void 0 ? void 0 : _f.split(",")) !== null && _g !== void 0 ? _g : [];
          if (links.length > 0) {
            links.forEach((link) => {
              const page = parseInt(link.split(";")[0].split("=")[1].substring(0, 1));
              const rel = JSON.parse(link.split(";")[1].split("=")[1]);
              pagination[`${rel}Page`] = page;
            });
            pagination.total = parseInt(total);
          }
          return { data: Object.assign(Object.assign({}, users), pagination), error: null };
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: { users: [] }, error };
          }
          throw error;
        }
      }
      /**
       * Get user by id.
       *
       * @param uid The user's unique identifier
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       *
       * @category Auth
       *
       * @remarks
       * - Fetches the user object from the database based on the user's id.
       * - The `getUserById()` method requires the user's id which maps to the `auth.users.id` column.
       *
       * @example Fetch the user object using the access_token jwt
       * ```js
       * const { data, error } = await supabase.auth.admin.getUserById(1)
       * ```
       *
       * @exampleResponse Fetch the user object using the access_token jwt
       * ```json
       * {
       *   data: {
       *     user: {
       *       id: '1',
       *       aud: 'authenticated',
       *       role: 'authenticated',
       *       email: 'example@email.com',
       *       email_confirmed_at: '2024-01-01T00:00:00Z',
       *       phone: '',
       *       confirmation_sent_at: '2024-01-01T00:00:00Z',
       *       confirmed_at: '2024-01-01T00:00:00Z',
       *       last_sign_in_at: '2024-01-01T00:00:00Z',
       *       app_metadata: {},
       *       user_metadata: {},
       *       identities: [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "id": "1",
       *           "user_id": "1",
       *           "identity_data": {
       *             "email": "example@email.com",
       *             "email_verified": true,
       *             "phone_verified": false,
       *             "sub": "1"
       *           },
       *           "provider": "email",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "email@example.com"
       *         },
       *       ],
       *       created_at: '2024-01-01T00:00:00Z',
       *       updated_at: '2024-01-01T00:00:00Z',
       *       is_anonymous: false,
       *     }
       *   }
       *   error: null
       * }
       * ```
       */
      async getUserById(uid) {
        (0, helpers_1.validateUUID)(uid);
        try {
          return await (0, fetch_1._request)(this.fetch, "GET", `${this.url}/admin/users/${uid}`, {
            headers: this.headers,
            xform: fetch_1._userResponse
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: { user: null }, error };
          }
          throw error;
        }
      }
      /**
       * Updates the user data. Changes are applied directly without confirmation flows.
       *
       * @param uid The user's unique identifier
       * @param attributes The data you want to update.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       *
       * @remarks
       * **Important:** This is a server-side operation and does **not** trigger client-side
       * `onAuthStateChange` listeners. The admin API has no connection to client state.
       *
       * To sync changes to the client after calling this method:
       * 1. On the client, call `supabase.auth.refreshSession()` to fetch the updated user data
       * 2. This will trigger the `TOKEN_REFRESHED` event and notify all listeners
       *
       * @example
       * ```typescript
       * // Server-side (Edge Function)
       * const { data, error } = await supabase.auth.admin.updateUserById(
       *   userId,
       *   { user_metadata: { preferences: { theme: 'dark' } } }
       * )
       *
       * // Client-side (to sync the changes)
       * const { data, error } = await supabase.auth.refreshSession()
       * // onAuthStateChange listeners will now be notified with updated user
       * ```
       *
       * @see {@link GoTrueClient.refreshSession} for syncing admin changes to the client
       * @see {@link GoTrueClient.updateUser} for client-side user updates (triggers listeners automatically)
       *
       * @category Auth
       *
       * @example Updates a user's email
       * ```js
       * const { data: user, error } = await supabase.auth.admin.updateUserById(
       *   '11111111-1111-1111-1111-111111111111',
       *   { email: 'new@email.com' }
       * )
       * ```
       *
       * @exampleResponse Updates a user's email
       * ```json
       * {
       *   "data": {
       *     "user": {
       *       "id": "11111111-1111-1111-1111-111111111111",
       *       "aud": "authenticated",
       *       "role": "authenticated",
       *       "email": "new@email.com",
       *       "email_confirmed_at": "2024-01-01T00:00:00Z",
       *       "phone": "",
       *       "confirmed_at": "2024-01-01T00:00:00Z",
       *       "recovery_sent_at": "2024-01-01T00:00:00Z",
       *       "last_sign_in_at": "2024-01-01T00:00:00Z",
       *       "app_metadata": {
       *         "provider": "email",
       *         "providers": [
       *           "email"
       *         ]
       *       },
       *       "user_metadata": {
       *         "email": "example@email.com",
       *         "email_verified": false,
       *         "phone_verified": false,
       *         "sub": "11111111-1111-1111-1111-111111111111"
       *       },
       *       "identities": [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "id": "11111111-1111-1111-1111-111111111111",
       *           "user_id": "11111111-1111-1111-1111-111111111111",
       *           "identity_data": {
       *             "email": "example@email.com",
       *             "email_verified": false,
       *             "phone_verified": false,
       *             "sub": "11111111-1111-1111-1111-111111111111"
       *           },
       *           "provider": "email",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "example@email.com"
       *         }
       *       ],
       *       "created_at": "2024-01-01T00:00:00Z",
       *       "updated_at": "2024-01-01T00:00:00Z",
       *       "is_anonymous": false
       *     }
       *   },
       *   "error": null
       * }
       * ```
       *
       * @example Updates a user's password
       * ```js
       * const { data: user, error } = await supabase.auth.admin.updateUserById(
       *   '6aa5d0d4-2a9f-4483-b6c8-0cf4c6c98ac4',
       *   { password: 'new_password' }
       * )
       * ```
       *
       * @example Updates a user's metadata
       * ```js
       * const { data: user, error } = await supabase.auth.admin.updateUserById(
       *   '6aa5d0d4-2a9f-4483-b6c8-0cf4c6c98ac4',
       *   { user_metadata: { hello: 'world' } }
       * )
       * ```
       *
       * @example Updates a user's app_metadata
       * ```js
       * const { data: user, error } = await supabase.auth.admin.updateUserById(
       *   '6aa5d0d4-2a9f-4483-b6c8-0cf4c6c98ac4',
       *   { app_metadata: { plan: 'trial' } }
       * )
       * ```
       *
       * @example Confirms a user's email address
       * ```js
       * const { data: user, error } = await supabase.auth.admin.updateUserById(
       *   '6aa5d0d4-2a9f-4483-b6c8-0cf4c6c98ac4',
       *   { email_confirm: true }
       * )
       * ```
       *
       * @example Confirms a user's phone number
       * ```js
       * const { data: user, error } = await supabase.auth.admin.updateUserById(
       *   '6aa5d0d4-2a9f-4483-b6c8-0cf4c6c98ac4',
       *   { phone_confirm: true }
       * )
       * ```
       *
       * @example Ban a user for 100 years
       * ```js
       * const { data: user, error } = await supabase.auth.admin.updateUserById(
       *   '6aa5d0d4-2a9f-4483-b6c8-0cf4c6c98ac4',
       *   { ban_duration: '876000h' }
       * )
       * ```
       */
      async updateUserById(uid, attributes) {
        (0, helpers_1.validateUUID)(uid);
        try {
          return await (0, fetch_1._request)(this.fetch, "PUT", `${this.url}/admin/users/${uid}`, {
            body: attributes,
            headers: this.headers,
            xform: fetch_1._userResponse
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: { user: null }, error };
          }
          throw error;
        }
      }
      /**
       * Delete a user. Requires a `service_role` key.
       *
       * @param id The user id you want to remove.
       * @param shouldSoftDelete If true, then the user will be soft-deleted from the auth schema. Soft deletion allows user identification from the hashed user ID but is not reversible.
       * Defaults to false for backward compatibility.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       *
       * @category Auth
       *
       * @remarks
       * - The `deleteUser()` method requires the user's ID, which maps to the `auth.users.id` column.
       *
       * @example Removes a user
       * ```js
       * const { data, error } = await supabase.auth.admin.deleteUser(
       *   '715ed5db-f090-4b8c-a067-640ecee36aa0'
       * )
       * ```
       *
       * @exampleResponse Removes a user
       * ```json
       * {
       *   "data": {
       *     "user": {}
       *   },
       *   "error": null
       * }
       * ```
       */
      async deleteUser(id, shouldSoftDelete = false) {
        (0, helpers_1.validateUUID)(id);
        try {
          return await (0, fetch_1._request)(this.fetch, "DELETE", `${this.url}/admin/users/${id}`, {
            headers: this.headers,
            body: {
              should_soft_delete: shouldSoftDelete
            },
            xform: fetch_1._userResponse
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: { user: null }, error };
          }
          throw error;
        }
      }
      async _listFactors(params) {
        (0, helpers_1.validateUUID)(params.userId);
        try {
          const { data, error } = await (0, fetch_1._request)(this.fetch, "GET", `${this.url}/admin/users/${params.userId}/factors`, {
            headers: this.headers,
            xform: (factors) => {
              return { data: { factors }, error: null };
            }
          });
          return { data, error };
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          throw error;
        }
      }
      async _deleteFactor(params) {
        (0, helpers_1.validateUUID)(params.userId);
        (0, helpers_1.validateUUID)(params.id);
        try {
          const data = await (0, fetch_1._request)(this.fetch, "DELETE", `${this.url}/admin/users/${params.userId}/factors/${params.id}`, {
            headers: this.headers
          });
          return { data, error: null };
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          throw error;
        }
      }
      /**
       * Lists all OAuth clients with optional pagination.
       * Only relevant when the OAuth 2.1 server is enabled in Supabase Auth.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       */
      async _listOAuthClients(params) {
        var _a, _b, _c, _d, _e, _f, _g;
        try {
          const pagination = { nextPage: null, lastPage: 0, total: 0 };
          const response2 = await (0, fetch_1._request)(this.fetch, "GET", `${this.url}/admin/oauth/clients`, {
            headers: this.headers,
            noResolveJson: true,
            query: {
              page: (_b = (_a = params === null || params === void 0 ? void 0 : params.page) === null || _a === void 0 ? void 0 : _a.toString()) !== null && _b !== void 0 ? _b : "",
              per_page: (_d = (_c = params === null || params === void 0 ? void 0 : params.perPage) === null || _c === void 0 ? void 0 : _c.toString()) !== null && _d !== void 0 ? _d : ""
            },
            xform: fetch_1._noResolveJsonResponse
          });
          if (response2.error)
            throw response2.error;
          const clients = await response2.json();
          const total = (_e = response2.headers.get("x-total-count")) !== null && _e !== void 0 ? _e : 0;
          const links = (_g = (_f = response2.headers.get("link")) === null || _f === void 0 ? void 0 : _f.split(",")) !== null && _g !== void 0 ? _g : [];
          if (links.length > 0) {
            links.forEach((link) => {
              const page = parseInt(link.split(";")[0].split("=")[1].substring(0, 1));
              const rel = JSON.parse(link.split(";")[1].split("=")[1]);
              pagination[`${rel}Page`] = page;
            });
            pagination.total = parseInt(total);
          }
          return { data: Object.assign(Object.assign({}, clients), pagination), error: null };
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: { clients: [] }, error };
          }
          throw error;
        }
      }
      /**
       * Creates a new OAuth client.
       * Only relevant when the OAuth 2.1 server is enabled in Supabase Auth.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       */
      async _createOAuthClient(params) {
        try {
          return await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/admin/oauth/clients`, {
            body: params,
            headers: this.headers,
            xform: (client) => {
              return { data: client, error: null };
            }
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          throw error;
        }
      }
      /**
       * Gets details of a specific OAuth client.
       * Only relevant when the OAuth 2.1 server is enabled in Supabase Auth.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       */
      async _getOAuthClient(clientId) {
        try {
          return await (0, fetch_1._request)(this.fetch, "GET", `${this.url}/admin/oauth/clients/${clientId}`, {
            headers: this.headers,
            xform: (client) => {
              return { data: client, error: null };
            }
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          throw error;
        }
      }
      /**
       * Updates an existing OAuth client.
       * Only relevant when the OAuth 2.1 server is enabled in Supabase Auth.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       */
      async _updateOAuthClient(clientId, params) {
        try {
          return await (0, fetch_1._request)(this.fetch, "PUT", `${this.url}/admin/oauth/clients/${clientId}`, {
            body: params,
            headers: this.headers,
            xform: (client) => {
              return { data: client, error: null };
            }
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          throw error;
        }
      }
      /**
       * Deletes an OAuth client.
       * Only relevant when the OAuth 2.1 server is enabled in Supabase Auth.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       */
      async _deleteOAuthClient(clientId) {
        try {
          await (0, fetch_1._request)(this.fetch, "DELETE", `${this.url}/admin/oauth/clients/${clientId}`, {
            headers: this.headers,
            noResolveJson: true
          });
          return { data: null, error: null };
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          throw error;
        }
      }
      /**
       * Regenerates the secret for an OAuth client.
       * Only relevant when the OAuth 2.1 server is enabled in Supabase Auth.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       */
      async _regenerateOAuthClientSecret(clientId) {
        try {
          return await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/admin/oauth/clients/${clientId}/regenerate_secret`, {
            headers: this.headers,
            xform: (client) => {
              return { data: client, error: null };
            }
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          throw error;
        }
      }
      /**
       * Lists all custom providers with optional type filter.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       */
      async _listCustomProviders(params) {
        try {
          const query = {};
          if (params === null || params === void 0 ? void 0 : params.type) {
            query.type = params.type;
          }
          return await (0, fetch_1._request)(this.fetch, "GET", `${this.url}/admin/custom-providers`, {
            headers: this.headers,
            query,
            xform: (data) => {
              var _a;
              return { data: { providers: (_a = data === null || data === void 0 ? void 0 : data.providers) !== null && _a !== void 0 ? _a : [] }, error: null };
            }
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: { providers: [] }, error };
          }
          throw error;
        }
      }
      /**
       * Creates a new custom OIDC/OAuth provider.
       *
       * For OIDC providers, the server fetches and validates the OpenID Connect discovery document
       * from the issuer's well-known endpoint (or the provided `discovery_url`) at creation time.
       * This may return a validation error (`error_code: "validation_failed"`) if the discovery
       * document is unreachable, not valid JSON, missing required fields, or if the issuer
       * in the document does not match the expected issuer.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       */
      async _createCustomProvider(params) {
        try {
          return await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/admin/custom-providers`, {
            body: params,
            headers: this.headers,
            xform: (provider) => {
              return { data: provider, error: null };
            }
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          throw error;
        }
      }
      /**
       * Gets details of a specific custom provider by identifier.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       */
      async _getCustomProvider(identifier) {
        try {
          return await (0, fetch_1._request)(this.fetch, "GET", `${this.url}/admin/custom-providers/${identifier}`, {
            headers: this.headers,
            xform: (provider) => {
              return { data: provider, error: null };
            }
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          throw error;
        }
      }
      /**
       * Updates an existing custom provider.
       *
       * When `issuer` or `discovery_url` is changed on an OIDC provider, the server re-fetches and
       * validates the discovery document before persisting. This may return a validation error
       * (`error_code: "validation_failed"`) if the discovery document is unreachable, invalid, or
       * the issuer does not match.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       */
      async _updateCustomProvider(identifier, params) {
        try {
          return await (0, fetch_1._request)(this.fetch, "PUT", `${this.url}/admin/custom-providers/${identifier}`, {
            body: params,
            headers: this.headers,
            xform: (provider) => {
              return { data: provider, error: null };
            }
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          throw error;
        }
      }
      /**
       * Deletes a custom provider.
       *
       * This function should only be called on a server. Never expose your `service_role` key in the browser.
       */
      async _deleteCustomProvider(identifier) {
        try {
          await (0, fetch_1._request)(this.fetch, "DELETE", `${this.url}/admin/custom-providers/${identifier}`, {
            headers: this.headers,
            noResolveJson: true
          });
          return { data: null, error: null };
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          throw error;
        }
      }
    };
    exports2.default = GoTrueAdminApi;
  }
});

// design/node_modules/@supabase/auth-js/dist/main/lib/local-storage.js
var require_local_storage = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/lib/local-storage.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.memoryLocalStorageAdapter = memoryLocalStorageAdapter;
    function memoryLocalStorageAdapter(store = {}) {
      return {
        getItem: (key) => {
          return store[key] || null;
        },
        setItem: (key, value) => {
          store[key] = value;
        },
        removeItem: (key) => {
          delete store[key];
        }
      };
    }
  }
});

// design/node_modules/@supabase/auth-js/dist/main/lib/locks.js
var require_locks = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/lib/locks.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.ProcessLockAcquireTimeoutError = exports2.NavigatorLockAcquireTimeoutError = exports2.LockAcquireTimeoutError = exports2.internals = void 0;
    exports2.navigatorLock = navigatorLock;
    exports2.processLock = processLock;
    var helpers_1 = require_helpers();
    exports2.internals = {
      /**
       * @experimental
       */
      debug: !!(globalThis && (0, helpers_1.supportsLocalStorage)() && globalThis.localStorage && globalThis.localStorage.getItem("supabase.gotrue-js.locks.debug") === "true")
    };
    var LockAcquireTimeoutError = class extends Error {
      constructor(message) {
        super(message);
        this.isAcquireTimeout = true;
      }
    };
    exports2.LockAcquireTimeoutError = LockAcquireTimeoutError;
    var NavigatorLockAcquireTimeoutError = class extends LockAcquireTimeoutError {
    };
    exports2.NavigatorLockAcquireTimeoutError = NavigatorLockAcquireTimeoutError;
    var ProcessLockAcquireTimeoutError = class extends LockAcquireTimeoutError {
    };
    exports2.ProcessLockAcquireTimeoutError = ProcessLockAcquireTimeoutError;
    async function navigatorLock(name, acquireTimeout, fn) {
      if (exports2.internals.debug) {
        console.log("@supabase/gotrue-js: navigatorLock: acquire lock", name, acquireTimeout);
      }
      const abortController = new globalThis.AbortController();
      let acquireTimeoutTimer;
      if (acquireTimeout > 0) {
        acquireTimeoutTimer = setTimeout(() => {
          abortController.abort();
          if (exports2.internals.debug) {
            console.log("@supabase/gotrue-js: navigatorLock acquire timed out", name);
          }
        }, acquireTimeout);
      }
      await Promise.resolve();
      try {
        return await globalThis.navigator.locks.request(name, acquireTimeout === 0 ? {
          mode: "exclusive",
          ifAvailable: true
        } : {
          mode: "exclusive",
          signal: abortController.signal
        }, async (lock) => {
          if (lock) {
            clearTimeout(acquireTimeoutTimer);
            if (exports2.internals.debug) {
              console.log("@supabase/gotrue-js: navigatorLock: acquired", name, lock.name);
            }
            try {
              return await fn();
            } finally {
              if (exports2.internals.debug) {
                console.log("@supabase/gotrue-js: navigatorLock: released", name, lock.name);
              }
            }
          } else {
            if (acquireTimeout === 0) {
              if (exports2.internals.debug) {
                console.log("@supabase/gotrue-js: navigatorLock: not immediately available", name);
              }
              throw new NavigatorLockAcquireTimeoutError(`Acquiring an exclusive Navigator LockManager lock "${name}" immediately failed`);
            } else {
              if (exports2.internals.debug) {
                try {
                  const result = await globalThis.navigator.locks.query();
                  console.log("@supabase/gotrue-js: Navigator LockManager state", JSON.stringify(result, null, "  "));
                } catch (e) {
                  console.warn("@supabase/gotrue-js: Error when querying Navigator LockManager state", e);
                }
              }
              console.warn("@supabase/gotrue-js: Navigator LockManager returned a null lock when using #request without ifAvailable set to true, it appears this browser is not following the LockManager spec https://developer.mozilla.org/en-US/docs/Web/API/LockManager/request");
              clearTimeout(acquireTimeoutTimer);
              return await fn();
            }
          }
        });
      } catch (e) {
        if (acquireTimeout > 0) {
          clearTimeout(acquireTimeoutTimer);
        }
        if ((e === null || e === void 0 ? void 0 : e.name) === "AbortError" && acquireTimeout > 0) {
          if (abortController.signal.aborted) {
            if (exports2.internals.debug) {
              console.log("@supabase/gotrue-js: navigatorLock: acquire timeout, recovering by stealing lock", name);
            }
            console.warn(`@supabase/gotrue-js: Lock "${name}" was not released within ${acquireTimeout}ms. This may indicate an orphaned lock from a component unmount (e.g., React Strict Mode). Forcefully acquiring the lock to recover.`);
            return await Promise.resolve().then(() => globalThis.navigator.locks.request(name, {
              mode: "exclusive",
              steal: true
            }, async (lock) => {
              if (lock) {
                if (exports2.internals.debug) {
                  console.log("@supabase/gotrue-js: navigatorLock: recovered (stolen)", name, lock.name);
                }
                try {
                  return await fn();
                } finally {
                  if (exports2.internals.debug) {
                    console.log("@supabase/gotrue-js: navigatorLock: released (stolen)", name, lock.name);
                  }
                }
              } else {
                console.warn("@supabase/gotrue-js: Navigator LockManager returned null lock even with steal: true");
                return await fn();
              }
            }));
          } else {
            if (exports2.internals.debug) {
              console.log("@supabase/gotrue-js: navigatorLock: lock was stolen by another request", name);
            }
            throw new NavigatorLockAcquireTimeoutError(`Lock "${name}" was released because another request stole it`);
          }
        }
        throw e;
      }
    }
    var PROCESS_LOCKS = {};
    async function processLock(name, acquireTimeout, fn) {
      var _a;
      const previousOperation = (_a = PROCESS_LOCKS[name]) !== null && _a !== void 0 ? _a : Promise.resolve();
      const previousOperationHandled = (async () => {
        try {
          await previousOperation;
          return null;
        } catch (e) {
          return null;
        }
      })();
      const currentOperation = (async () => {
        let timeoutId = null;
        try {
          const timeoutPromise = acquireTimeout >= 0 ? new Promise((_, reject) => {
            timeoutId = setTimeout(() => {
              console.warn(`@supabase/gotrue-js: Lock "${name}" acquisition timed out after ${acquireTimeout}ms. This may be caused by another operation holding the lock. Consider increasing lockAcquireTimeout or checking for stuck operations.`);
              reject(new ProcessLockAcquireTimeoutError(`Acquiring process lock with name "${name}" timed out`));
            }, acquireTimeout);
          }) : null;
          await Promise.race([previousOperationHandled, timeoutPromise].filter((x) => x));
          if (timeoutId !== null) {
            clearTimeout(timeoutId);
          }
        } catch (e) {
          if (timeoutId !== null) {
            clearTimeout(timeoutId);
          }
          if (e && e.isAcquireTimeout) {
            throw e;
          }
        }
        return await fn();
      })();
      PROCESS_LOCKS[name] = (async () => {
        try {
          return await currentOperation;
        } catch (e) {
          if (e && e.isAcquireTimeout) {
            try {
              await previousOperation;
            } catch (prevError) {
            }
            return null;
          }
          throw e;
        }
      })();
      return await currentOperation;
    }
  }
});

// design/node_modules/@supabase/auth-js/dist/main/lib/polyfills.js
var require_polyfills = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/lib/polyfills.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.polyfillGlobalThis = polyfillGlobalThis;
    function polyfillGlobalThis() {
      if (typeof globalThis === "object")
        return;
      try {
        Object.defineProperty(Object.prototype, "__magic__", {
          get: function() {
            return this;
          },
          configurable: true
        });
        __magic__.globalThis = __magic__;
        delete Object.prototype.__magic__;
      } catch (e) {
        if (typeof self !== "undefined") {
          self.globalThis = self;
        }
      }
    }
  }
});

// design/node_modules/@supabase/auth-js/dist/main/lib/web3/ethereum.js
var require_ethereum = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/lib/web3/ethereum.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.getAddress = getAddress;
    exports2.fromHex = fromHex;
    exports2.toHex = toHex;
    exports2.createSiweMessage = createSiweMessage;
    function getAddress(address) {
      if (!/^0x[a-fA-F0-9]{40}$/.test(address)) {
        throw new Error(`@supabase/auth-js: Address "${address}" is invalid.`);
      }
      return address.toLowerCase();
    }
    function fromHex(hex) {
      return parseInt(hex, 16);
    }
    function toHex(value) {
      const bytes = new TextEncoder().encode(value);
      const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
      return "0x" + hex;
    }
    function createSiweMessage(parameters) {
      var _a;
      const { chainId, domain, expirationTime, issuedAt = /* @__PURE__ */ new Date(), nonce, notBefore, requestId, resources, scheme, uri, version: version3 } = parameters;
      {
        if (!Number.isInteger(chainId))
          throw new Error(`@supabase/auth-js: Invalid SIWE message field "chainId". Chain ID must be a EIP-155 chain ID. Provided value: ${chainId}`);
        if (!domain)
          throw new Error(`@supabase/auth-js: Invalid SIWE message field "domain". Domain must be provided.`);
        if (nonce && nonce.length < 8)
          throw new Error(`@supabase/auth-js: Invalid SIWE message field "nonce". Nonce must be at least 8 characters. Provided value: ${nonce}`);
        if (!uri)
          throw new Error(`@supabase/auth-js: Invalid SIWE message field "uri". URI must be provided.`);
        if (version3 !== "1")
          throw new Error(`@supabase/auth-js: Invalid SIWE message field "version". Version must be '1'. Provided value: ${version3}`);
        if ((_a = parameters.statement) === null || _a === void 0 ? void 0 : _a.includes("\n"))
          throw new Error(`@supabase/auth-js: Invalid SIWE message field "statement". Statement must not include '\\n'. Provided value: ${parameters.statement}`);
      }
      const address = getAddress(parameters.address);
      const origin = scheme ? `${scheme}://${domain}` : domain;
      const statement = parameters.statement ? `${parameters.statement}
` : "";
      const prefix = `${origin} wants you to sign in with your Ethereum account:
${address}

${statement}`;
      let suffix = `URI: ${uri}
Version: ${version3}
Chain ID: ${chainId}${nonce ? `
Nonce: ${nonce}` : ""}
Issued At: ${issuedAt.toISOString()}`;
      if (expirationTime)
        suffix += `
Expiration Time: ${expirationTime.toISOString()}`;
      if (notBefore)
        suffix += `
Not Before: ${notBefore.toISOString()}`;
      if (requestId)
        suffix += `
Request ID: ${requestId}`;
      if (resources) {
        let content = "\nResources:";
        for (const resource of resources) {
          if (!resource || typeof resource !== "string")
            throw new Error(`@supabase/auth-js: Invalid SIWE message field "resources". Every resource must be a valid string. Provided value: ${resource}`);
          content += `
- ${resource}`;
        }
        suffix += content;
      }
      return `${prefix}
${suffix}`;
    }
  }
});

// design/node_modules/@supabase/auth-js/dist/main/lib/webauthn.errors.js
var require_webauthn_errors = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/lib/webauthn.errors.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.WebAuthnUnknownError = exports2.WebAuthnError = void 0;
    exports2.isWebAuthnError = isWebAuthnError;
    exports2.identifyRegistrationError = identifyRegistrationError;
    exports2.identifyAuthenticationError = identifyAuthenticationError;
    var webauthn_1 = require_webauthn();
    var WebAuthnError = class extends Error {
      constructor({ message, code, cause, name }) {
        var _a;
        super(message, { cause });
        this.__isWebAuthnError = true;
        this.name = (_a = name !== null && name !== void 0 ? name : cause instanceof Error ? cause.name : void 0) !== null && _a !== void 0 ? _a : "Unknown Error";
        this.code = code;
      }
    };
    exports2.WebAuthnError = WebAuthnError;
    var WebAuthnUnknownError = class extends WebAuthnError {
      constructor(message, originalError) {
        super({
          code: "ERROR_PASSTHROUGH_SEE_CAUSE_PROPERTY",
          cause: originalError,
          message
        });
        this.name = "WebAuthnUnknownError";
        this.originalError = originalError;
      }
    };
    exports2.WebAuthnUnknownError = WebAuthnUnknownError;
    function isWebAuthnError(error) {
      return typeof error === "object" && error !== null && "__isWebAuthnError" in error;
    }
    function identifyRegistrationError({ error, options }) {
      var _a, _b, _c;
      const { publicKey } = options;
      if (!publicKey) {
        throw Error("options was missing required publicKey property");
      }
      if (error.name === "AbortError") {
        if (options.signal instanceof AbortSignal) {
          return new WebAuthnError({
            message: "Registration ceremony was sent an abort signal",
            code: "ERROR_CEREMONY_ABORTED",
            cause: error
          });
        }
      } else if (error.name === "ConstraintError") {
        if (((_a = publicKey.authenticatorSelection) === null || _a === void 0 ? void 0 : _a.requireResidentKey) === true) {
          return new WebAuthnError({
            message: "Discoverable credentials were required but no available authenticator supported it",
            code: "ERROR_AUTHENTICATOR_MISSING_DISCOVERABLE_CREDENTIAL_SUPPORT",
            cause: error
          });
        } else if (
          // @ts-ignore: `mediation` doesn't yet exist on CredentialCreationOptions but it's possible as of Sept 2024
          options.mediation === "conditional" && ((_b = publicKey.authenticatorSelection) === null || _b === void 0 ? void 0 : _b.userVerification) === "required"
        ) {
          return new WebAuthnError({
            message: "User verification was required during automatic registration but it could not be performed",
            code: "ERROR_AUTO_REGISTER_USER_VERIFICATION_FAILURE",
            cause: error
          });
        } else if (((_c = publicKey.authenticatorSelection) === null || _c === void 0 ? void 0 : _c.userVerification) === "required") {
          return new WebAuthnError({
            message: "User verification was required but no available authenticator supported it",
            code: "ERROR_AUTHENTICATOR_MISSING_USER_VERIFICATION_SUPPORT",
            cause: error
          });
        }
      } else if (error.name === "InvalidStateError") {
        return new WebAuthnError({
          message: "The authenticator was previously registered",
          code: "ERROR_AUTHENTICATOR_PREVIOUSLY_REGISTERED",
          cause: error
        });
      } else if (error.name === "NotAllowedError") {
        return new WebAuthnError({
          message: error.message,
          code: "ERROR_PASSTHROUGH_SEE_CAUSE_PROPERTY",
          cause: error
        });
      } else if (error.name === "NotSupportedError") {
        const validPubKeyCredParams = publicKey.pubKeyCredParams.filter((param) => param.type === "public-key");
        if (validPubKeyCredParams.length === 0) {
          return new WebAuthnError({
            message: 'No entry in pubKeyCredParams was of type "public-key"',
            code: "ERROR_MALFORMED_PUBKEYCREDPARAMS",
            cause: error
          });
        }
        return new WebAuthnError({
          message: "No available authenticator supported any of the specified pubKeyCredParams algorithms",
          code: "ERROR_AUTHENTICATOR_NO_SUPPORTED_PUBKEYCREDPARAMS_ALG",
          cause: error
        });
      } else if (error.name === "SecurityError") {
        const effectiveDomain = window.location.hostname;
        if (!(0, webauthn_1.isValidDomain)(effectiveDomain)) {
          return new WebAuthnError({
            message: `${window.location.hostname} is an invalid domain`,
            code: "ERROR_INVALID_DOMAIN",
            cause: error
          });
        } else if (publicKey.rp.id !== effectiveDomain) {
          return new WebAuthnError({
            message: `The RP ID "${publicKey.rp.id}" is invalid for this domain`,
            code: "ERROR_INVALID_RP_ID",
            cause: error
          });
        }
      } else if (error.name === "TypeError") {
        if (publicKey.user.id.byteLength < 1 || publicKey.user.id.byteLength > 64) {
          return new WebAuthnError({
            message: "User ID was not between 1 and 64 characters",
            code: "ERROR_INVALID_USER_ID_LENGTH",
            cause: error
          });
        }
      } else if (error.name === "UnknownError") {
        return new WebAuthnError({
          message: "The authenticator was unable to process the specified options, or could not create a new credential",
          code: "ERROR_AUTHENTICATOR_GENERAL_ERROR",
          cause: error
        });
      }
      return new WebAuthnError({
        message: "a Non-Webauthn related error has occurred",
        code: "ERROR_PASSTHROUGH_SEE_CAUSE_PROPERTY",
        cause: error
      });
    }
    function identifyAuthenticationError({ error, options }) {
      const { publicKey } = options;
      if (!publicKey) {
        throw Error("options was missing required publicKey property");
      }
      if (error.name === "AbortError") {
        if (options.signal instanceof AbortSignal) {
          return new WebAuthnError({
            message: "Authentication ceremony was sent an abort signal",
            code: "ERROR_CEREMONY_ABORTED",
            cause: error
          });
        }
      } else if (error.name === "NotAllowedError") {
        return new WebAuthnError({
          message: error.message,
          code: "ERROR_PASSTHROUGH_SEE_CAUSE_PROPERTY",
          cause: error
        });
      } else if (error.name === "SecurityError") {
        const effectiveDomain = window.location.hostname;
        if (!(0, webauthn_1.isValidDomain)(effectiveDomain)) {
          return new WebAuthnError({
            message: `${window.location.hostname} is an invalid domain`,
            code: "ERROR_INVALID_DOMAIN",
            cause: error
          });
        } else if (publicKey.rpId !== effectiveDomain) {
          return new WebAuthnError({
            message: `The RP ID "${publicKey.rpId}" is invalid for this domain`,
            code: "ERROR_INVALID_RP_ID",
            cause: error
          });
        }
      } else if (error.name === "UnknownError") {
        return new WebAuthnError({
          message: "The authenticator was unable to process the specified options, or could not create a new assertion signature",
          code: "ERROR_AUTHENTICATOR_GENERAL_ERROR",
          cause: error
        });
      }
      return new WebAuthnError({
        message: "a Non-Webauthn related error has occurred",
        code: "ERROR_PASSTHROUGH_SEE_CAUSE_PROPERTY",
        cause: error
      });
    }
  }
});

// design/node_modules/@supabase/auth-js/dist/main/lib/webauthn.js
var require_webauthn = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/lib/webauthn.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.WebAuthnApi = exports2.DEFAULT_REQUEST_OPTIONS = exports2.DEFAULT_CREATION_OPTIONS = exports2.webAuthnAbortService = exports2.WebAuthnAbortService = exports2.identifyAuthenticationError = exports2.identifyRegistrationError = exports2.isWebAuthnError = exports2.WebAuthnError = void 0;
    exports2.deserializeCredentialCreationOptions = deserializeCredentialCreationOptions;
    exports2.deserializeCredentialRequestOptions = deserializeCredentialRequestOptions;
    exports2.serializeCredentialCreationResponse = serializeCredentialCreationResponse;
    exports2.serializeCredentialRequestResponse = serializeCredentialRequestResponse;
    exports2.isValidDomain = isValidDomain;
    exports2.createCredential = createCredential;
    exports2.getCredential = getCredential;
    exports2.mergeCredentialCreationOptions = mergeCredentialCreationOptions;
    exports2.mergeCredentialRequestOptions = mergeCredentialRequestOptions;
    var tslib_1 = (init_tslib_es6(), __toCommonJS(tslib_es6_exports));
    var base64url_1 = require_base64url();
    var errors_1 = require_errors();
    var helpers_1 = require_helpers();
    var webauthn_errors_1 = require_webauthn_errors();
    Object.defineProperty(exports2, "identifyAuthenticationError", { enumerable: true, get: function() {
      return webauthn_errors_1.identifyAuthenticationError;
    } });
    Object.defineProperty(exports2, "identifyRegistrationError", { enumerable: true, get: function() {
      return webauthn_errors_1.identifyRegistrationError;
    } });
    Object.defineProperty(exports2, "isWebAuthnError", { enumerable: true, get: function() {
      return webauthn_errors_1.isWebAuthnError;
    } });
    Object.defineProperty(exports2, "WebAuthnError", { enumerable: true, get: function() {
      return webauthn_errors_1.WebAuthnError;
    } });
    var WebAuthnAbortService = class {
      /**
       * Create an abort signal for a new WebAuthn operation.
       * Automatically cancels any existing operation.
       *
       * @returns {AbortSignal} Signal to pass to navigator.credentials.create() or .get()
       * @see {@link https://developer.mozilla.org/en-US/docs/Web/API/AbortSignal MDN - AbortSignal}
       */
      createNewAbortSignal() {
        if (this.controller) {
          const abortError = new Error("Cancelling existing WebAuthn API call for new one");
          abortError.name = "AbortError";
          this.controller.abort(abortError);
        }
        const newController = new AbortController();
        this.controller = newController;
        return newController.signal;
      }
      /**
       * Manually cancel the current WebAuthn operation.
       * Useful for cleaning up when user cancels or navigates away.
       *
       * @see {@link https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort MDN - AbortController.abort}
       */
      cancelCeremony() {
        if (this.controller) {
          const abortError = new Error("Manually cancelling existing WebAuthn API call");
          abortError.name = "AbortError";
          this.controller.abort(abortError);
          this.controller = void 0;
        }
      }
    };
    exports2.WebAuthnAbortService = WebAuthnAbortService;
    exports2.webAuthnAbortService = new WebAuthnAbortService();
    function deserializeCredentialCreationOptions(options) {
      if (!options) {
        throw new Error("Credential creation options are required");
      }
      if (typeof PublicKeyCredential !== "undefined" && "parseCreationOptionsFromJSON" in PublicKeyCredential && typeof PublicKeyCredential.parseCreationOptionsFromJSON === "function") {
        return PublicKeyCredential.parseCreationOptionsFromJSON(
          /** we assert the options here as typescript still doesn't know about future webauthn types */
          options
        );
      }
      const { challenge: challengeStr, user: userOpts, excludeCredentials } = options, restOptions = tslib_1.__rest(
        options,
        ["challenge", "user", "excludeCredentials"]
      );
      const challenge = (0, base64url_1.base64UrlToUint8Array)(challengeStr).buffer;
      const user = Object.assign(Object.assign({}, userOpts), { id: (0, base64url_1.base64UrlToUint8Array)(userOpts.id).buffer });
      const result = Object.assign(Object.assign({}, restOptions), {
        challenge,
        user
      });
      if (excludeCredentials && excludeCredentials.length > 0) {
        result.excludeCredentials = new Array(excludeCredentials.length);
        for (let i = 0; i < excludeCredentials.length; i++) {
          const cred = excludeCredentials[i];
          result.excludeCredentials[i] = Object.assign(Object.assign({}, cred), {
            id: (0, base64url_1.base64UrlToUint8Array)(cred.id).buffer,
            type: cred.type || "public-key",
            // Cast transports to handle future transport types like "cable"
            transports: cred.transports
          });
        }
      }
      return result;
    }
    function deserializeCredentialRequestOptions(options) {
      if (!options) {
        throw new Error("Credential request options are required");
      }
      if (typeof PublicKeyCredential !== "undefined" && "parseRequestOptionsFromJSON" in PublicKeyCredential && typeof PublicKeyCredential.parseRequestOptionsFromJSON === "function") {
        return PublicKeyCredential.parseRequestOptionsFromJSON(options);
      }
      const { challenge: challengeStr, allowCredentials } = options, restOptions = tslib_1.__rest(
        options,
        ["challenge", "allowCredentials"]
      );
      const challenge = (0, base64url_1.base64UrlToUint8Array)(challengeStr).buffer;
      const result = Object.assign(Object.assign({}, restOptions), { challenge });
      if (allowCredentials && allowCredentials.length > 0) {
        result.allowCredentials = new Array(allowCredentials.length);
        for (let i = 0; i < allowCredentials.length; i++) {
          const cred = allowCredentials[i];
          result.allowCredentials[i] = Object.assign(Object.assign({}, cred), {
            id: (0, base64url_1.base64UrlToUint8Array)(cred.id).buffer,
            type: cred.type || "public-key",
            // Cast transports to handle future transport types like "cable"
            transports: cred.transports
          });
        }
      }
      return result;
    }
    function serializeCredentialCreationResponse(credential) {
      var _a;
      if ("toJSON" in credential && typeof credential.toJSON === "function") {
        return credential.toJSON();
      }
      const credentialWithAttachment = credential;
      return {
        id: credential.id,
        rawId: credential.id,
        response: {
          attestationObject: (0, base64url_1.bytesToBase64URL)(new Uint8Array(credential.response.attestationObject)),
          clientDataJSON: (0, base64url_1.bytesToBase64URL)(new Uint8Array(credential.response.clientDataJSON))
        },
        type: "public-key",
        clientExtensionResults: credential.getClientExtensionResults(),
        // Convert null to undefined and cast to AuthenticatorAttachment type
        authenticatorAttachment: (_a = credentialWithAttachment.authenticatorAttachment) !== null && _a !== void 0 ? _a : void 0
      };
    }
    function serializeCredentialRequestResponse(credential) {
      var _a;
      if ("toJSON" in credential && typeof credential.toJSON === "function") {
        return credential.toJSON();
      }
      const credentialWithAttachment = credential;
      const clientExtensionResults = credential.getClientExtensionResults();
      const assertionResponse = credential.response;
      return {
        id: credential.id,
        rawId: credential.id,
        // W3C spec expects rawId to match id for JSON format
        response: {
          authenticatorData: (0, base64url_1.bytesToBase64URL)(new Uint8Array(assertionResponse.authenticatorData)),
          clientDataJSON: (0, base64url_1.bytesToBase64URL)(new Uint8Array(assertionResponse.clientDataJSON)),
          signature: (0, base64url_1.bytesToBase64URL)(new Uint8Array(assertionResponse.signature)),
          userHandle: assertionResponse.userHandle ? (0, base64url_1.bytesToBase64URL)(new Uint8Array(assertionResponse.userHandle)) : void 0
        },
        type: "public-key",
        clientExtensionResults,
        // Convert null to undefined and cast to AuthenticatorAttachment type
        authenticatorAttachment: (_a = credentialWithAttachment.authenticatorAttachment) !== null && _a !== void 0 ? _a : void 0
      };
    }
    function isValidDomain(hostname) {
      return (
        // Consider localhost valid as well since it's okay wrt Secure Contexts
        hostname === "localhost" || /^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$/i.test(hostname)
      );
    }
    function browserSupportsWebAuthn() {
      var _a, _b;
      return !!((0, helpers_1.isBrowser)() && "PublicKeyCredential" in window && window.PublicKeyCredential && "credentials" in navigator && typeof ((_a = navigator === null || navigator === void 0 ? void 0 : navigator.credentials) === null || _a === void 0 ? void 0 : _a.create) === "function" && typeof ((_b = navigator === null || navigator === void 0 ? void 0 : navigator.credentials) === null || _b === void 0 ? void 0 : _b.get) === "function");
    }
    async function createCredential(options) {
      try {
        const response2 = await navigator.credentials.create(
          /** we assert the type here until typescript types are updated */
          options
        );
        if (!response2) {
          return {
            data: null,
            error: new webauthn_errors_1.WebAuthnUnknownError("Empty credential response", response2)
          };
        }
        if (!(response2 instanceof PublicKeyCredential)) {
          return {
            data: null,
            error: new webauthn_errors_1.WebAuthnUnknownError("Browser returned unexpected credential type", response2)
          };
        }
        return { data: response2, error: null };
      } catch (err) {
        return {
          data: null,
          error: (0, webauthn_errors_1.identifyRegistrationError)({
            error: err,
            options
          })
        };
      }
    }
    async function getCredential(options) {
      try {
        const response2 = await navigator.credentials.get(
          /** we assert the type here until typescript types are updated */
          options
        );
        if (!response2) {
          return {
            data: null,
            error: new webauthn_errors_1.WebAuthnUnknownError("Empty credential response", response2)
          };
        }
        if (!(response2 instanceof PublicKeyCredential)) {
          return {
            data: null,
            error: new webauthn_errors_1.WebAuthnUnknownError("Browser returned unexpected credential type", response2)
          };
        }
        return { data: response2, error: null };
      } catch (err) {
        return {
          data: null,
          error: (0, webauthn_errors_1.identifyAuthenticationError)({
            error: err,
            options
          })
        };
      }
    }
    exports2.DEFAULT_CREATION_OPTIONS = {
      hints: ["security-key"],
      authenticatorSelection: {
        authenticatorAttachment: "cross-platform",
        requireResidentKey: false,
        /** set to preferred because older yubikeys don't have PIN/Biometric */
        userVerification: "preferred",
        residentKey: "discouraged"
      },
      attestation: "direct"
    };
    exports2.DEFAULT_REQUEST_OPTIONS = {
      /** set to preferred because older yubikeys don't have PIN/Biometric */
      userVerification: "preferred",
      hints: ["security-key"],
      attestation: "direct"
    };
    function deepMerge(...sources) {
      const isObject = (val) => val !== null && typeof val === "object" && !Array.isArray(val);
      const isArrayBufferLike = (val) => val instanceof ArrayBuffer || ArrayBuffer.isView(val);
      const result = {};
      for (const source of sources) {
        if (!source)
          continue;
        for (const key in source) {
          const value = source[key];
          if (value === void 0)
            continue;
          if (Array.isArray(value)) {
            result[key] = value;
          } else if (isArrayBufferLike(value)) {
            result[key] = value;
          } else if (isObject(value)) {
            const existing = result[key];
            if (isObject(existing)) {
              result[key] = deepMerge(existing, value);
            } else {
              result[key] = deepMerge(value);
            }
          } else {
            result[key] = value;
          }
        }
      }
      return result;
    }
    function mergeCredentialCreationOptions(baseOptions, overrides) {
      return deepMerge(exports2.DEFAULT_CREATION_OPTIONS, baseOptions, overrides || {});
    }
    function mergeCredentialRequestOptions(baseOptions, overrides) {
      return deepMerge(exports2.DEFAULT_REQUEST_OPTIONS, baseOptions, overrides || {});
    }
    var WebAuthnApi = class {
      constructor(client) {
        this.client = client;
        this.enroll = this._enroll.bind(this);
        this.challenge = this._challenge.bind(this);
        this.verify = this._verify.bind(this);
        this.authenticate = this._authenticate.bind(this);
        this.register = this._register.bind(this);
      }
      /**
       * Enroll a new WebAuthn factor.
       * Creates an unverified WebAuthn factor that must be verified with a credential.
       *
       * @experimental This method is experimental and may change in future releases
       * @param {Omit<MFAEnrollWebauthnParams, 'factorType'>} params - Enrollment parameters (friendlyName required)
       * @returns {Promise<AuthMFAEnrollWebauthnResponse>} Enrolled factor details or error
       * @see {@link https://w3c.github.io/webauthn/#sctn-registering-a-new-credential W3C WebAuthn Spec - Registering a New Credential}
       */
      async _enroll(params) {
        return this.client.mfa.enroll(Object.assign(Object.assign({}, params), { factorType: "webauthn" }));
      }
      /**
       * Challenge for WebAuthn credential creation or authentication.
       * Combines server challenge with browser credential operations.
       * Handles both registration (create) and authentication (request) flows.
       *
       * @experimental This method is experimental and may change in future releases
       * @param {MFAChallengeWebauthnParams & { friendlyName?: string; signal?: AbortSignal }} params - Challenge parameters including factorId
       * @param {Object} overrides - Allows you to override the parameters passed to navigator.credentials
       * @param {PublicKeyCredentialCreationOptionsFuture} overrides.create - Override options for credential creation
       * @param {PublicKeyCredentialRequestOptionsFuture} overrides.request - Override options for credential request
       * @returns {Promise<RequestResult>} Challenge response with credential or error
       * @see {@link https://w3c.github.io/webauthn/#sctn-credential-creation W3C WebAuthn Spec - Credential Creation}
       * @see {@link https://w3c.github.io/webauthn/#sctn-verifying-assertion W3C WebAuthn Spec - Verifying Assertion}
       */
      async _challenge({ factorId, webauthn, friendlyName, signal }, overrides) {
        var _a;
        try {
          const { data: challengeResponse, error: challengeError } = await this.client.mfa.challenge({
            factorId,
            webauthn
          });
          if (!challengeResponse) {
            return { data: null, error: challengeError };
          }
          const abortSignal = signal !== null && signal !== void 0 ? signal : exports2.webAuthnAbortService.createNewAbortSignal();
          if (challengeResponse.webauthn.type === "create") {
            const { user } = challengeResponse.webauthn.credential_options.publicKey;
            if (!user.name) {
              const nameToUse = friendlyName;
              if (!nameToUse) {
                const currentUser = await this.client.getUser();
                const userData = currentUser.data.user;
                const fallbackName = ((_a = userData === null || userData === void 0 ? void 0 : userData.user_metadata) === null || _a === void 0 ? void 0 : _a.name) || (userData === null || userData === void 0 ? void 0 : userData.email) || (userData === null || userData === void 0 ? void 0 : userData.id) || "User";
                user.name = `${user.id}:${fallbackName}`;
              } else {
                user.name = `${user.id}:${nameToUse}`;
              }
            }
            if (!user.displayName) {
              user.displayName = user.name;
            }
          }
          switch (challengeResponse.webauthn.type) {
            case "create": {
              const options = mergeCredentialCreationOptions(challengeResponse.webauthn.credential_options.publicKey, overrides === null || overrides === void 0 ? void 0 : overrides.create);
              const { data, error } = await createCredential({
                publicKey: options,
                signal: abortSignal
              });
              if (data) {
                return {
                  data: {
                    factorId,
                    challengeId: challengeResponse.id,
                    webauthn: {
                      type: challengeResponse.webauthn.type,
                      credential_response: data
                    }
                  },
                  error: null
                };
              }
              return { data: null, error };
            }
            case "request": {
              const options = mergeCredentialRequestOptions(challengeResponse.webauthn.credential_options.publicKey, overrides === null || overrides === void 0 ? void 0 : overrides.request);
              const { data, error } = await getCredential(Object.assign(Object.assign({}, challengeResponse.webauthn.credential_options), { publicKey: options, signal: abortSignal }));
              if (data) {
                return {
                  data: {
                    factorId,
                    challengeId: challengeResponse.id,
                    webauthn: {
                      type: challengeResponse.webauthn.type,
                      credential_response: data
                    }
                  },
                  error: null
                };
              }
              return { data: null, error };
            }
          }
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          return {
            data: null,
            error: new errors_1.AuthUnknownError("Unexpected error in challenge", error)
          };
        }
      }
      /**
       * Verify a WebAuthn credential with the server.
       * Completes the WebAuthn ceremony by sending the credential to the server for verification.
       *
       * @experimental This method is experimental and may change in future releases
       * @param {Object} params - Verification parameters
       * @param {string} params.challengeId - ID of the challenge being verified
       * @param {string} params.factorId - ID of the WebAuthn factor
       * @param {MFAVerifyWebauthnParams<T>['webauthn']} params.webauthn - WebAuthn credential response
       * @returns {Promise<AuthMFAVerifyResponse>} Verification result with session or error
       * @see {@link https://w3c.github.io/webauthn/#sctn-verifying-assertion W3C WebAuthn Spec - Verifying an Authentication Assertion}
       * */
      async _verify({ challengeId, factorId, webauthn }) {
        return this.client.mfa.verify({
          factorId,
          challengeId,
          webauthn
        });
      }
      /**
       * Complete WebAuthn authentication flow.
       * Performs challenge and verification in a single operation for existing credentials.
       *
       * @experimental This method is experimental and may change in future releases
       * @param {Object} params - Authentication parameters
       * @param {string} params.factorId - ID of the WebAuthn factor to authenticate with
       * @param {Object} params.webauthn - WebAuthn configuration
       * @param {string} params.webauthn.rpId - Relying Party ID (defaults to current hostname)
       * @param {string[]} params.webauthn.rpOrigins - Allowed origins (defaults to current origin)
       * @param {AbortSignal} params.webauthn.signal - Optional abort signal
       * @param {PublicKeyCredentialRequestOptionsFuture} overrides - Override options for navigator.credentials.get
       * @returns {Promise<RequestResult<AuthMFAVerifyResponseData, WebAuthnError | AuthError>>} Authentication result
       * @see {@link https://w3c.github.io/webauthn/#sctn-authentication W3C WebAuthn Spec - Authentication Ceremony}
       * @see {@link https://developer.mozilla.org/en-US/docs/Web/API/PublicKeyCredentialRequestOptions MDN - PublicKeyCredentialRequestOptions}
       */
      async _authenticate({ factorId, webauthn: { rpId = typeof window !== "undefined" ? window.location.hostname : void 0, rpOrigins = typeof window !== "undefined" ? [window.location.origin] : void 0, signal } = {} }, overrides) {
        if (!rpId) {
          return {
            data: null,
            error: new errors_1.AuthError("rpId is required for WebAuthn authentication")
          };
        }
        try {
          if (!browserSupportsWebAuthn()) {
            return {
              data: null,
              error: new errors_1.AuthUnknownError("Browser does not support WebAuthn", null)
            };
          }
          const { data: challengeResponse, error: challengeError } = await this.challenge({
            factorId,
            webauthn: { rpId, rpOrigins },
            signal
          }, { request: overrides });
          if (!challengeResponse) {
            return { data: null, error: challengeError };
          }
          const { webauthn } = challengeResponse;
          return this._verify({
            factorId,
            challengeId: challengeResponse.challengeId,
            webauthn: {
              type: webauthn.type,
              rpId,
              rpOrigins,
              credential_response: webauthn.credential_response
            }
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          return {
            data: null,
            error: new errors_1.AuthUnknownError("Unexpected error in authenticate", error)
          };
        }
      }
      /**
       * Complete WebAuthn registration flow.
       * Performs enrollment, challenge, and verification in a single operation for new credentials.
       *
       * @experimental This method is experimental and may change in future releases
       * @param {Object} params - Registration parameters
       * @param {string} params.friendlyName - User-friendly name for the credential
       * @param {string} params.rpId - Relying Party ID (defaults to current hostname)
       * @param {string[]} params.rpOrigins - Allowed origins (defaults to current origin)
       * @param {AbortSignal} params.signal - Optional abort signal
       * @param {PublicKeyCredentialCreationOptionsFuture} overrides - Override options for navigator.credentials.create
       * @returns {Promise<RequestResult<AuthMFAVerifyResponseData, WebAuthnError | AuthError>>} Registration result
       * @see {@link https://w3c.github.io/webauthn/#sctn-registering-a-new-credential W3C WebAuthn Spec - Registration Ceremony}
       * @see {@link https://developer.mozilla.org/en-US/docs/Web/API/PublicKeyCredentialCreationOptions MDN - PublicKeyCredentialCreationOptions}
       */
      async _register({ friendlyName, webauthn: { rpId = typeof window !== "undefined" ? window.location.hostname : void 0, rpOrigins = typeof window !== "undefined" ? [window.location.origin] : void 0, signal } = {} }, overrides) {
        if (!rpId) {
          return {
            data: null,
            error: new errors_1.AuthError("rpId is required for WebAuthn registration")
          };
        }
        try {
          if (!browserSupportsWebAuthn()) {
            return {
              data: null,
              error: new errors_1.AuthUnknownError("Browser does not support WebAuthn", null)
            };
          }
          const { data: factor, error: enrollError } = await this._enroll({
            friendlyName
          });
          if (!factor) {
            await this.client.mfa.listFactors().then((factors) => {
              var _a;
              return (_a = factors.data) === null || _a === void 0 ? void 0 : _a.all.find((v) => v.factor_type === "webauthn" && v.friendly_name === friendlyName && v.status !== "unverified");
            }).then((factor2) => factor2 ? this.client.mfa.unenroll({ factorId: factor2 === null || factor2 === void 0 ? void 0 : factor2.id }) : void 0);
            return { data: null, error: enrollError };
          }
          const { data: challengeResponse, error: challengeError } = await this._challenge({
            factorId: factor.id,
            friendlyName: factor.friendly_name,
            webauthn: { rpId, rpOrigins },
            signal
          }, {
            create: overrides
          });
          if (!challengeResponse) {
            return { data: null, error: challengeError };
          }
          return this._verify({
            factorId: factor.id,
            challengeId: challengeResponse.challengeId,
            webauthn: {
              rpId,
              rpOrigins,
              type: challengeResponse.webauthn.type,
              credential_response: challengeResponse.webauthn.credential_response
            }
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return { data: null, error };
          }
          return {
            data: null,
            error: new errors_1.AuthUnknownError("Unexpected error in register", error)
          };
        }
      }
    };
    exports2.WebAuthnApi = WebAuthnApi;
  }
});

// design/node_modules/@supabase/auth-js/dist/main/GoTrueClient.js
var require_GoTrueClient = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/GoTrueClient.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    var tslib_1 = (init_tslib_es6(), __toCommonJS(tslib_es6_exports));
    var GoTrueAdminApi_1 = tslib_1.__importDefault(require_GoTrueAdminApi());
    var constants_1 = require_constants2();
    var errors_1 = require_errors();
    var fetch_1 = require_fetch();
    var helpers_1 = require_helpers();
    var local_storage_1 = require_local_storage();
    var locks_1 = require_locks();
    var polyfills_1 = require_polyfills();
    var version_1 = require_version2();
    var base64url_1 = require_base64url();
    var ethereum_1 = require_ethereum();
    var webauthn_1 = require_webauthn();
    (0, polyfills_1.polyfillGlobalThis)();
    var DEFAULT_OPTIONS = {
      url: constants_1.GOTRUE_URL,
      storageKey: constants_1.STORAGE_KEY,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
      headers: constants_1.DEFAULT_HEADERS,
      flowType: "implicit",
      debug: false,
      hasCustomAuthorizationHeader: false,
      throwOnError: false,
      lockAcquireTimeout: 5e3,
      // 5 seconds
      skipAutoInitialize: false
    };
    async function lockNoOp(name, acquireTimeout, fn) {
      return await fn();
    }
    var GLOBAL_JWKS = {};
    var GoTrueClient = class _GoTrueClient {
      /**
       * The JWKS used for verifying asymmetric JWTs
       */
      get jwks() {
        var _a, _b;
        return (_b = (_a = GLOBAL_JWKS[this.storageKey]) === null || _a === void 0 ? void 0 : _a.jwks) !== null && _b !== void 0 ? _b : { keys: [] };
      }
      set jwks(value) {
        GLOBAL_JWKS[this.storageKey] = Object.assign(Object.assign({}, GLOBAL_JWKS[this.storageKey]), { jwks: value });
      }
      get jwks_cached_at() {
        var _a, _b;
        return (_b = (_a = GLOBAL_JWKS[this.storageKey]) === null || _a === void 0 ? void 0 : _a.cachedAt) !== null && _b !== void 0 ? _b : Number.MIN_SAFE_INTEGER;
      }
      set jwks_cached_at(value) {
        GLOBAL_JWKS[this.storageKey] = Object.assign(Object.assign({}, GLOBAL_JWKS[this.storageKey]), { cachedAt: value });
      }
      /**
       * Create a new client for use in the browser.
       *
       * @example Using supabase-js (recommended)
       * ```ts
       * import { createClient } from '@supabase/supabase-js'
       *
       * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key')
       * const { data, error } = await supabase.auth.getUser()
       * ```
       *
       * @example Standalone import for bundle-sensitive environments
       * ```ts
       * import { GoTrueClient } from '@supabase/auth-js'
       *
       * const auth = new GoTrueClient({
       *   url: 'https://xyzcompany.supabase.co/auth/v1',
       *   headers: { apikey: 'publishable-or-anon-key' },
       *   storageKey: 'supabase-auth',
       * })
       * ```
       */
      constructor(options) {
        var _a, _b, _c;
        this.userStorage = null;
        this.memoryStorage = null;
        this.stateChangeEmitters = /* @__PURE__ */ new Map();
        this.autoRefreshTicker = null;
        this.autoRefreshTickTimeout = null;
        this.visibilityChangedCallback = null;
        this.refreshingDeferred = null;
        this.initializePromise = null;
        this.detectSessionInUrl = true;
        this.hasCustomAuthorizationHeader = false;
        this.suppressGetSessionWarning = false;
        this.lockAcquired = false;
        this.pendingInLock = [];
        this.broadcastChannel = null;
        this.logger = console.log;
        const settings = Object.assign(Object.assign({}, DEFAULT_OPTIONS), options);
        this.storageKey = settings.storageKey;
        this.instanceID = (_a = _GoTrueClient.nextInstanceID[this.storageKey]) !== null && _a !== void 0 ? _a : 0;
        _GoTrueClient.nextInstanceID[this.storageKey] = this.instanceID + 1;
        this.logDebugMessages = !!settings.debug;
        if (typeof settings.debug === "function") {
          this.logger = settings.debug;
        }
        if (this.instanceID > 0 && (0, helpers_1.isBrowser)()) {
          const message = `${this._logPrefix()} Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.`;
          console.warn(message);
          if (this.logDebugMessages) {
            console.trace(message);
          }
        }
        this.persistSession = settings.persistSession;
        this.autoRefreshToken = settings.autoRefreshToken;
        this.admin = new GoTrueAdminApi_1.default({
          url: settings.url,
          headers: settings.headers,
          fetch: settings.fetch
        });
        this.url = settings.url;
        this.headers = settings.headers;
        this.fetch = (0, helpers_1.resolveFetch)(settings.fetch);
        this.lock = settings.lock || lockNoOp;
        this.detectSessionInUrl = settings.detectSessionInUrl;
        this.flowType = settings.flowType;
        this.hasCustomAuthorizationHeader = settings.hasCustomAuthorizationHeader;
        this.throwOnError = settings.throwOnError;
        this.lockAcquireTimeout = settings.lockAcquireTimeout;
        if (settings.lock) {
          this.lock = settings.lock;
        } else if (this.persistSession && (0, helpers_1.isBrowser)() && ((_b = globalThis === null || globalThis === void 0 ? void 0 : globalThis.navigator) === null || _b === void 0 ? void 0 : _b.locks)) {
          this.lock = locks_1.navigatorLock;
        } else {
          this.lock = lockNoOp;
        }
        if (!this.jwks) {
          this.jwks = { keys: [] };
          this.jwks_cached_at = Number.MIN_SAFE_INTEGER;
        }
        this.mfa = {
          verify: this._verify.bind(this),
          enroll: this._enroll.bind(this),
          unenroll: this._unenroll.bind(this),
          challenge: this._challenge.bind(this),
          listFactors: this._listFactors.bind(this),
          challengeAndVerify: this._challengeAndVerify.bind(this),
          getAuthenticatorAssuranceLevel: this._getAuthenticatorAssuranceLevel.bind(this),
          webauthn: new webauthn_1.WebAuthnApi(this)
        };
        this.oauth = {
          getAuthorizationDetails: this._getAuthorizationDetails.bind(this),
          approveAuthorization: this._approveAuthorization.bind(this),
          denyAuthorization: this._denyAuthorization.bind(this),
          listGrants: this._listOAuthGrants.bind(this),
          revokeGrant: this._revokeOAuthGrant.bind(this)
        };
        if (this.persistSession) {
          if (settings.storage) {
            this.storage = settings.storage;
          } else {
            if ((0, helpers_1.supportsLocalStorage)()) {
              this.storage = globalThis.localStorage;
            } else {
              this.memoryStorage = {};
              this.storage = (0, local_storage_1.memoryLocalStorageAdapter)(this.memoryStorage);
            }
          }
          if (settings.userStorage) {
            this.userStorage = settings.userStorage;
          }
        } else {
          this.memoryStorage = {};
          this.storage = (0, local_storage_1.memoryLocalStorageAdapter)(this.memoryStorage);
        }
        if ((0, helpers_1.isBrowser)() && globalThis.BroadcastChannel && this.persistSession && this.storageKey) {
          try {
            this.broadcastChannel = new globalThis.BroadcastChannel(this.storageKey);
          } catch (e) {
            console.error("Failed to create a new BroadcastChannel, multi-tab state changes will not be available", e);
          }
          (_c = this.broadcastChannel) === null || _c === void 0 ? void 0 : _c.addEventListener("message", async (event) => {
            this._debug("received broadcast notification from other tab or client", event);
            try {
              await this._notifyAllSubscribers(event.data.event, event.data.session, false);
            } catch (error) {
              this._debug("#broadcastChannel", "error", error);
            }
          });
        }
        if (!settings.skipAutoInitialize) {
          this.initialize().catch((error) => {
            this._debug("#initialize()", "error", error);
          });
        }
      }
      /**
       * Returns whether error throwing mode is enabled for this client.
       */
      isThrowOnErrorEnabled() {
        return this.throwOnError;
      }
      /**
       * Centralizes return handling with optional error throwing. When `throwOnError` is enabled
       * and the provided result contains a non-nullish error, the error is thrown instead of
       * being returned. This ensures consistent behavior across all public API methods.
       */
      _returnResult(result) {
        if (this.throwOnError && result && result.error) {
          throw result.error;
        }
        return result;
      }
      _logPrefix() {
        return `GoTrueClient@${this.storageKey}:${this.instanceID} (${version_1.version}) ${(/* @__PURE__ */ new Date()).toISOString()}`;
      }
      _debug(...args) {
        if (this.logDebugMessages) {
          this.logger(this._logPrefix(), ...args);
        }
        return this;
      }
      /**
       * Initializes the client session either from the url or from storage.
       * This method is automatically called when instantiating the client, but should also be called
       * manually when checking for an error from an auth redirect (oauth, magiclink, password recovery, etc).
       *
       * @category Auth
       */
      async initialize() {
        if (this.initializePromise) {
          return await this.initializePromise;
        }
        this.initializePromise = (async () => {
          return await this._acquireLock(this.lockAcquireTimeout, async () => {
            return await this._initialize();
          });
        })();
        return await this.initializePromise;
      }
      /**
       * IMPORTANT:
       * 1. Never throw in this method, as it is called from the constructor
       * 2. Never return a session from this method as it would be cached over
       *    the whole lifetime of the client
       */
      async _initialize() {
        var _a;
        try {
          let params = {};
          let callbackUrlType = "none";
          if ((0, helpers_1.isBrowser)()) {
            params = (0, helpers_1.parseParametersFromURL)(window.location.href);
            if (this._isImplicitGrantCallback(params)) {
              callbackUrlType = "implicit";
            } else if (await this._isPKCECallback(params)) {
              callbackUrlType = "pkce";
            }
          }
          if ((0, helpers_1.isBrowser)() && this.detectSessionInUrl && callbackUrlType !== "none") {
            const { data, error } = await this._getSessionFromURL(params, callbackUrlType);
            if (error) {
              this._debug("#_initialize()", "error detecting session from URL", error);
              if ((0, errors_1.isAuthImplicitGrantRedirectError)(error)) {
                const errorCode = (_a = error.details) === null || _a === void 0 ? void 0 : _a.code;
                if (errorCode === "identity_already_exists" || errorCode === "identity_not_found" || errorCode === "single_identity_not_deletable") {
                  return { error };
                }
              }
              return { error };
            }
            const { session, redirectType } = data;
            this._debug("#_initialize()", "detected session in URL", session, "redirect type", redirectType);
            await this._saveSession(session);
            setTimeout(async () => {
              if (redirectType === "recovery") {
                await this._notifyAllSubscribers("PASSWORD_RECOVERY", session);
              } else {
                await this._notifyAllSubscribers("SIGNED_IN", session);
              }
            }, 0);
            return { error: null };
          }
          await this._recoverAndRefresh();
          return { error: null };
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ error });
          }
          return this._returnResult({
            error: new errors_1.AuthUnknownError("Unexpected error during initialization", error)
          });
        } finally {
          await this._handleVisibilityChange();
          this._debug("#_initialize()", "end");
        }
      }
      /**
       * Creates a new anonymous user.
       *
       * @returns A session where the is_anonymous claim in the access token JWT set to true
       *
       * @category Auth
       *
       * @remarks
       * - Returns an anonymous user
       * - It is recommended to set up captcha for anonymous sign-ins to prevent abuse. You can pass in the captcha token in the `options` param.
       *
       * @example Create an anonymous user
       * ```js
       * const { data, error } = await supabase.auth.signInAnonymously({
       *   options: {
       *     captchaToken
       *   }
       * });
       * ```
       *
       * @exampleResponse Create an anonymous user
       * ```json
       * {
       *   "data": {
       *     "user": {
       *       "id": "11111111-1111-1111-1111-111111111111",
       *       "aud": "authenticated",
       *       "role": "authenticated",
       *       "email": "",
       *       "phone": "",
       *       "last_sign_in_at": "2024-01-01T00:00:00Z",
       *       "app_metadata": {},
       *       "user_metadata": {},
       *       "identities": [],
       *       "created_at": "2024-01-01T00:00:00Z",
       *       "updated_at": "2024-01-01T00:00:00Z",
       *       "is_anonymous": true
       *     },
       *     "session": {
       *       "access_token": "<ACCESS_TOKEN>",
       *       "token_type": "bearer",
       *       "expires_in": 3600,
       *       "expires_at": 1700000000,
       *       "refresh_token": "<REFRESH_TOKEN>",
       *       "user": {
       *         "id": "11111111-1111-1111-1111-111111111111",
       *         "aud": "authenticated",
       *         "role": "authenticated",
       *         "email": "",
       *         "phone": "",
       *         "last_sign_in_at": "2024-01-01T00:00:00Z",
       *         "app_metadata": {},
       *         "user_metadata": {},
       *         "identities": [],
       *         "created_at": "2024-01-01T00:00:00Z",
       *         "updated_at": "2024-01-01T00:00:00Z",
       *         "is_anonymous": true
       *       }
       *     }
       *   },
       *   "error": null
       * }
       * ```
       *
       * @example Create an anonymous user with custom user metadata
       * ```js
       * const { data, error } = await supabase.auth.signInAnonymously({
       *   options: {
       *     data
       *   }
       * })
       * ```
       */
      async signInAnonymously(credentials) {
        var _a, _b, _c;
        try {
          const res = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/signup`, {
            headers: this.headers,
            body: {
              data: (_b = (_a = credentials === null || credentials === void 0 ? void 0 : credentials.options) === null || _a === void 0 ? void 0 : _a.data) !== null && _b !== void 0 ? _b : {},
              gotrue_meta_security: { captcha_token: (_c = credentials === null || credentials === void 0 ? void 0 : credentials.options) === null || _c === void 0 ? void 0 : _c.captchaToken }
            },
            xform: fetch_1._sessionResponse
          });
          const { data, error } = res;
          if (error || !data) {
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          const session = data.session;
          const user = data.user;
          if (data.session) {
            await this._saveSession(data.session);
            await this._notifyAllSubscribers("SIGNED_IN", session);
          }
          return this._returnResult({ data: { user, session }, error: null });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          throw error;
        }
      }
      /**
       * Creates a new user.
       *
       * Be aware that if a user account exists in the system you may get back an
       * error message that attempts to hide this information from the user.
       * This method has support for PKCE via email signups. The PKCE flow cannot be used when autoconfirm is enabled.
       *
       * @returns A logged-in session if the server has "autoconfirm" ON
       * @returns A user if the server has "autoconfirm" OFF
       *
       * @category Auth
       *
       * @remarks
       * - By default, the user needs to verify their email address before logging in. To turn this off, disable **Confirm email** in [your project](/dashboard/project/_/auth/providers).
       * - **Confirm email** determines if users need to confirm their email address after signing up.
       *   - If **Confirm email** is enabled, a `user` is returned but `session` is null.
       *   - If **Confirm email** is disabled, both a `user` and a `session` are returned.
       * - When the user confirms their email address, they are redirected to the [`SITE_URL`](/docs/guides/auth/redirect-urls#use-wildcards-in-redirect-urls) by default. You can modify your `SITE_URL` or add additional redirect URLs in [your project](/dashboard/project/_/auth/url-configuration).
       * - If signUp() is called for an existing confirmed user:
       *   - When both **Confirm email** and **Confirm phone** (even when phone provider is disabled) are enabled in [your project](/dashboard/project/_/auth/providers), an obfuscated/fake user object is returned.
       *   - When either **Confirm email** or **Confirm phone** (even when phone provider is disabled) is disabled, the error message, `User already registered` is returned.
       * - To fetch the currently logged-in user, refer to [`getUser()`](/docs/reference/javascript/auth-getuser).
       *
       * @example Sign up with an email and password
       * ```js
       * const { data, error } = await supabase.auth.signUp({
       *   email: 'example@email.com',
       *   password: 'example-password',
       * })
       * ```
       *
       * @exampleResponse Sign up with an email and password
       * ```json
       * // Some fields may be null if "confirm email" is enabled.
       * {
       *   "data": {
       *     "user": {
       *       "id": "11111111-1111-1111-1111-111111111111",
       *       "aud": "authenticated",
       *       "role": "authenticated",
       *       "email": "example@email.com",
       *       "email_confirmed_at": "2024-01-01T00:00:00Z",
       *       "phone": "",
       *       "last_sign_in_at": "2024-01-01T00:00:00Z",
       *       "app_metadata": {
       *         "provider": "email",
       *         "providers": [
       *           "email"
       *         ]
       *       },
       *       "user_metadata": {},
       *       "identities": [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "id": "11111111-1111-1111-1111-111111111111",
       *           "user_id": "11111111-1111-1111-1111-111111111111",
       *           "identity_data": {
       *             "email": "example@email.com",
       *             "email_verified": false,
       *             "phone_verified": false,
       *             "sub": "11111111-1111-1111-1111-111111111111"
       *           },
       *           "provider": "email",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "example@email.com"
       *         }
       *       ],
       *       "created_at": "2024-01-01T00:00:00Z",
       *       "updated_at": "2024-01-01T00:00:00Z"
       *     },
       *     "session": {
       *       "access_token": "<ACCESS_TOKEN>",
       *       "token_type": "bearer",
       *       "expires_in": 3600,
       *       "expires_at": 1700000000,
       *       "refresh_token": "<REFRESH_TOKEN>",
       *       "user": {
       *         "id": "11111111-1111-1111-1111-111111111111",
       *         "aud": "authenticated",
       *         "role": "authenticated",
       *         "email": "example@email.com",
       *         "email_confirmed_at": "2024-01-01T00:00:00Z",
       *         "phone": "",
       *         "last_sign_in_at": "2024-01-01T00:00:00Z",
       *         "app_metadata": {
       *           "provider": "email",
       *           "providers": [
       *             "email"
       *           ]
       *         },
       *         "user_metadata": {},
       *         "identities": [
       *           {
       *             "identity_id": "22222222-2222-2222-2222-222222222222",
       *             "id": "11111111-1111-1111-1111-111111111111",
       *             "user_id": "11111111-1111-1111-1111-111111111111",
       *             "identity_data": {
       *               "email": "example@email.com",
       *               "email_verified": false,
       *               "phone_verified": false,
       *               "sub": "11111111-1111-1111-1111-111111111111"
       *             },
       *             "provider": "email",
       *             "last_sign_in_at": "2024-01-01T00:00:00Z",
       *             "created_at": "2024-01-01T00:00:00Z",
       *             "updated_at": "2024-01-01T00:00:00Z",
       *             "email": "example@email.com"
       *           }
       *         ],
       *         "created_at": "2024-01-01T00:00:00Z",
       *         "updated_at": "2024-01-01T00:00:00Z"
       *       }
       *     }
       *   },
       *   "error": null
       * }
       * ```
       *
       * @example Sign up with a phone number and password (SMS)
       * ```js
       * const { data, error } = await supabase.auth.signUp({
       *   phone: '123456789',
       *   password: 'example-password',
       *   options: {
       *     channel: 'sms'
       *   }
       * })
       * ```
       *
       * @exampleDescription Sign up with a phone number and password (whatsapp)
       * The user will be sent a WhatsApp message which contains a OTP. By default, a given user can only request a OTP once every 60 seconds. Note that a user will need to have a valid WhatsApp account that is linked to Twilio in order to use this feature.
       *
       * @example Sign up with a phone number and password (whatsapp)
       * ```js
       * const { data, error } = await supabase.auth.signUp({
       *   phone: '123456789',
       *   password: 'example-password',
       *   options: {
       *     channel: 'whatsapp'
       *   }
       * })
       * ```
       *
       * @example Sign up with additional user metadata
       * ```js
       * const { data, error } = await supabase.auth.signUp(
       *   {
       *     email: 'example@email.com',
       *     password: 'example-password',
       *     options: {
       *       data: {
       *         first_name: 'John',
       *         age: 27,
       *       }
       *     }
       *   }
       * )
       * ```
       *
       * @exampleDescription Sign up with a redirect URL
       * - See [redirect URLs and wildcards](/docs/guides/auth/redirect-urls#use-wildcards-in-redirect-urls) to add additional redirect URLs to your project.
       *
       * @example Sign up with a redirect URL
       * ```js
       * const { data, error } = await supabase.auth.signUp(
       *   {
       *     email: 'example@email.com',
       *     password: 'example-password',
       *     options: {
       *       emailRedirectTo: 'https://example.com/welcome'
       *     }
       *   }
       * )
       * ```
       */
      async signUp(credentials) {
        var _a, _b, _c;
        try {
          let res;
          if ("email" in credentials) {
            const { email, password, options } = credentials;
            let codeChallenge = null;
            let codeChallengeMethod = null;
            if (this.flowType === "pkce") {
              ;
              [codeChallenge, codeChallengeMethod] = await (0, helpers_1.getCodeChallengeAndMethod)(this.storage, this.storageKey);
            }
            res = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/signup`, {
              headers: this.headers,
              redirectTo: options === null || options === void 0 ? void 0 : options.emailRedirectTo,
              body: {
                email,
                password,
                data: (_a = options === null || options === void 0 ? void 0 : options.data) !== null && _a !== void 0 ? _a : {},
                gotrue_meta_security: { captcha_token: options === null || options === void 0 ? void 0 : options.captchaToken },
                code_challenge: codeChallenge,
                code_challenge_method: codeChallengeMethod
              },
              xform: fetch_1._sessionResponse
            });
          } else if ("phone" in credentials) {
            const { phone, password, options } = credentials;
            res = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/signup`, {
              headers: this.headers,
              body: {
                phone,
                password,
                data: (_b = options === null || options === void 0 ? void 0 : options.data) !== null && _b !== void 0 ? _b : {},
                channel: (_c = options === null || options === void 0 ? void 0 : options.channel) !== null && _c !== void 0 ? _c : "sms",
                gotrue_meta_security: { captcha_token: options === null || options === void 0 ? void 0 : options.captchaToken }
              },
              xform: fetch_1._sessionResponse
            });
          } else {
            throw new errors_1.AuthInvalidCredentialsError("You must provide either an email or phone number and a password");
          }
          const { data, error } = res;
          if (error || !data) {
            await (0, helpers_1.removeItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          const session = data.session;
          const user = data.user;
          if (data.session) {
            await this._saveSession(data.session);
            await this._notifyAllSubscribers("SIGNED_IN", session);
          }
          return this._returnResult({ data: { user, session }, error: null });
        } catch (error) {
          await (0, helpers_1.removeItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          throw error;
        }
      }
      /**
       * Log in an existing user with an email and password or phone and password.
       *
       * Be aware that you may get back an error message that will not distinguish
       * between the cases where the account does not exist or that the
       * email/phone and password combination is wrong or that the account can only
       * be accessed via social login.
       *
       * @category Auth
       *
       * @remarks
       * - Requires either an email and password or a phone number and password.
       *
       * @example Sign in with email and password
       * ```js
       * const { data, error } = await supabase.auth.signInWithPassword({
       *   email: 'example@email.com',
       *   password: 'example-password',
       * })
       * ```
       *
       * @exampleResponse Sign in with email and password
       * ```json
       * {
       *   "data": {
       *     "user": {
       *       "id": "11111111-1111-1111-1111-111111111111",
       *       "aud": "authenticated",
       *       "role": "authenticated",
       *       "email": "example@email.com",
       *       "email_confirmed_at": "2024-01-01T00:00:00Z",
       *       "phone": "",
       *       "last_sign_in_at": "2024-01-01T00:00:00Z",
       *       "app_metadata": {
       *         "provider": "email",
       *         "providers": [
       *           "email"
       *         ]
       *       },
       *       "user_metadata": {},
       *       "identities": [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "id": "11111111-1111-1111-1111-111111111111",
       *           "user_id": "11111111-1111-1111-1111-111111111111",
       *           "identity_data": {
       *             "email": "example@email.com",
       *             "email_verified": false,
       *             "phone_verified": false,
       *             "sub": "11111111-1111-1111-1111-111111111111"
       *           },
       *           "provider": "email",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "example@email.com"
       *         }
       *       ],
       *       "created_at": "2024-01-01T00:00:00Z",
       *       "updated_at": "2024-01-01T00:00:00Z"
       *     },
       *     "session": {
       *       "access_token": "<ACCESS_TOKEN>",
       *       "token_type": "bearer",
       *       "expires_in": 3600,
       *       "expires_at": 1700000000,
       *       "refresh_token": "<REFRESH_TOKEN>",
       *       "user": {
       *         "id": "11111111-1111-1111-1111-111111111111",
       *         "aud": "authenticated",
       *         "role": "authenticated",
       *         "email": "example@email.com",
       *         "email_confirmed_at": "2024-01-01T00:00:00Z",
       *         "phone": "",
       *         "last_sign_in_at": "2024-01-01T00:00:00Z",
       *         "app_metadata": {
       *           "provider": "email",
       *           "providers": [
       *             "email"
       *           ]
       *         },
       *         "user_metadata": {},
       *         "identities": [
       *           {
       *             "identity_id": "22222222-2222-2222-2222-222222222222",
       *             "id": "11111111-1111-1111-1111-111111111111",
       *             "user_id": "11111111-1111-1111-1111-111111111111",
       *             "identity_data": {
       *               "email": "example@email.com",
       *               "email_verified": false,
       *               "phone_verified": false,
       *               "sub": "11111111-1111-1111-1111-111111111111"
       *             },
       *             "provider": "email",
       *             "last_sign_in_at": "2024-01-01T00:00:00Z",
       *             "created_at": "2024-01-01T00:00:00Z",
       *             "updated_at": "2024-01-01T00:00:00Z",
       *             "email": "example@email.com"
       *           }
       *         ],
       *         "created_at": "2024-01-01T00:00:00Z",
       *         "updated_at": "2024-01-01T00:00:00Z"
       *       }
       *     }
       *   },
       *   "error": null
       * }
       * ```
       *
       * @example Sign in with phone and password
       * ```js
       * const { data, error } = await supabase.auth.signInWithPassword({
       *   phone: '+13334445555',
       *   password: 'some-password',
       * })
       * ```
       */
      async signInWithPassword(credentials) {
        try {
          let res;
          if ("email" in credentials) {
            const { email, password, options } = credentials;
            res = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/token?grant_type=password`, {
              headers: this.headers,
              body: {
                email,
                password,
                gotrue_meta_security: { captcha_token: options === null || options === void 0 ? void 0 : options.captchaToken }
              },
              xform: fetch_1._sessionResponsePassword
            });
          } else if ("phone" in credentials) {
            const { phone, password, options } = credentials;
            res = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/token?grant_type=password`, {
              headers: this.headers,
              body: {
                phone,
                password,
                gotrue_meta_security: { captcha_token: options === null || options === void 0 ? void 0 : options.captchaToken }
              },
              xform: fetch_1._sessionResponsePassword
            });
          } else {
            throw new errors_1.AuthInvalidCredentialsError("You must provide either an email or phone number and a password");
          }
          const { data, error } = res;
          if (error) {
            return this._returnResult({ data: { user: null, session: null }, error });
          } else if (!data || !data.session || !data.user) {
            const invalidTokenError = new errors_1.AuthInvalidTokenResponseError();
            return this._returnResult({ data: { user: null, session: null }, error: invalidTokenError });
          }
          if (data.session) {
            await this._saveSession(data.session);
            await this._notifyAllSubscribers("SIGNED_IN", data.session);
          }
          return this._returnResult({
            data: Object.assign({ user: data.user, session: data.session }, data.weak_password ? { weakPassword: data.weak_password } : null),
            error
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          throw error;
        }
      }
      /**
       * Log in an existing user via a third-party provider.
       * This method supports the PKCE flow.
       *
       * @category Auth
       *
       * @remarks
       * - This method is used for signing in using [Social Login (OAuth) providers](/docs/guides/auth#configure-third-party-providers).
       * - It works by redirecting your application to the provider's authorization screen, before bringing back the user to your app.
       *
       * @example Sign in using a third-party provider
       * ```js
       * const { data, error } = await supabase.auth.signInWithOAuth({
       *   provider: 'github'
       * })
       * ```
       *
       * @exampleResponse Sign in using a third-party provider
       * ```json
       * {
       *   data: {
       *     provider: 'github',
       *     url: <PROVIDER_URL_TO_REDIRECT_TO>
       *   },
       *   error: null
       * }
       * ```
       *
       * @exampleDescription Sign in using a third-party provider with redirect
       * - When the OAuth provider successfully authenticates the user, they are redirected to the URL specified in the `redirectTo` parameter. This parameter defaults to the [`SITE_URL`](/docs/guides/auth/redirect-urls#use-wildcards-in-redirect-urls). It does not redirect the user immediately after invoking this method.
       * - See [redirect URLs and wildcards](/docs/guides/auth/redirect-urls#use-wildcards-in-redirect-urls) to add additional redirect URLs to your project.
       *
       * @example Sign in using a third-party provider with redirect
       * ```js
       * const { data, error } = await supabase.auth.signInWithOAuth({
       *   provider: 'github',
       *   options: {
       *     redirectTo: 'https://example.com/welcome'
       *   }
       * })
       * ```
       *
       * @exampleDescription Sign in with scopes and access provider tokens
       * If you need additional access from an OAuth provider, in order to access provider specific APIs in the name of the user, you can do this by passing in the scopes the user should authorize for your application. Note that the `scopes` option takes in **a space-separated list** of scopes.
       *
       * Because OAuth sign-in often includes redirects, you should register an `onAuthStateChange` callback immediately after you create the Supabase client. This callback will listen for the presence of `provider_token` and `provider_refresh_token` properties on the `session` object and store them in local storage. The client library will emit these values **only once** immediately after the user signs in. You can then access them by looking them up in local storage, or send them to your backend servers for further processing.
       *
       * Finally, make sure you remove them from local storage on the `SIGNED_OUT` event. If the OAuth provider supports token revocation, make sure you call those APIs either from the frontend or schedule them to be called on the backend.
       *
       * @example Sign in with scopes and access provider tokens
       * ```js
       * // Register this immediately after calling createClient!
       * // Because signInWithOAuth causes a redirect, you need to fetch the
       * // provider tokens from the callback.
       * supabase.auth.onAuthStateChange((event, session) => {
       *   if (session && session.provider_token) {
       *     window.localStorage.setItem('oauth_provider_token', session.provider_token)
       *   }
       *
       *   if (session && session.provider_refresh_token) {
       *     window.localStorage.setItem('oauth_provider_refresh_token', session.provider_refresh_token)
       *   }
       *
       *   if (event === 'SIGNED_OUT') {
       *     window.localStorage.removeItem('oauth_provider_token')
       *     window.localStorage.removeItem('oauth_provider_refresh_token')
       *   }
       * })
       *
       * // Call this on your Sign in with GitHub button to initiate OAuth
       * // with GitHub with the requested elevated scopes.
       * await supabase.auth.signInWithOAuth({
       *   provider: 'github',
       *   options: {
       *     scopes: 'repo gist notifications'
       *   }
       * })
       * ```
       */
      async signInWithOAuth(credentials) {
        var _a, _b, _c, _d;
        return await this._handleProviderSignIn(credentials.provider, {
          redirectTo: (_a = credentials.options) === null || _a === void 0 ? void 0 : _a.redirectTo,
          scopes: (_b = credentials.options) === null || _b === void 0 ? void 0 : _b.scopes,
          queryParams: (_c = credentials.options) === null || _c === void 0 ? void 0 : _c.queryParams,
          skipBrowserRedirect: (_d = credentials.options) === null || _d === void 0 ? void 0 : _d.skipBrowserRedirect
        });
      }
      /**
       * Log in an existing user by exchanging an Auth Code issued during the PKCE flow.
       *
       * @category Auth
       *
       * @remarks
       * - Used when `flowType` is set to `pkce` in client options.
       *
       * @example Exchange Auth Code
       * ```js
       * supabase.auth.exchangeCodeForSession('34e770dd-9ff9-416c-87fa-43b31d7ef225')
       * ```
       *
       * @exampleResponse Exchange Auth Code
       * ```json
       * {
       *   "data": {
       *     session: {
       *       access_token: '<ACCESS_TOKEN>',
       *       token_type: 'bearer',
       *       expires_in: 3600,
       *       expires_at: 1700000000,
       *       refresh_token: '<REFRESH_TOKEN>',
       *       user: {
       *         id: '11111111-1111-1111-1111-111111111111',
       *         aud: 'authenticated',
       *         role: 'authenticated',
       *         email: 'example@email.com'
       *         email_confirmed_at: '2024-01-01T00:00:00Z',
       *         phone: '',
       *         confirmation_sent_at: '2024-01-01T00:00:00Z',
       *         confirmed_at: '2024-01-01T00:00:00Z',
       *         last_sign_in_at: '2024-01-01T00:00:00Z',
       *         app_metadata: {
       *           "provider": "email",
       *           "providers": [
       *             "email",
       *             "<OTHER_PROVIDER>"
       *           ]
       *         },
       *         user_metadata: {
       *           email: 'email@email.com',
       *           email_verified: true,
       *           full_name: 'User Name',
       *           iss: '<ISS>',
       *           name: 'User Name',
       *           phone_verified: false,
       *           provider_id: '<PROVIDER_ID>',
       *           sub: '<SUB>'
       *         },
       *         identities: [
       *           {
       *             "identity_id": "22222222-2222-2222-2222-222222222222",
       *             "id": "11111111-1111-1111-1111-111111111111",
       *             "user_id": "11111111-1111-1111-1111-111111111111",
       *             "identity_data": {
       *               "email": "example@email.com",
       *               "email_verified": false,
       *               "phone_verified": false,
       *               "sub": "11111111-1111-1111-1111-111111111111"
       *             },
       *             "provider": "email",
       *             "last_sign_in_at": "2024-01-01T00:00:00Z",
       *             "created_at": "2024-01-01T00:00:00Z",
       *             "updated_at": "2024-01-01T00:00:00Z",
       *             "email": "email@example.com"
       *           },
       *           {
       *             "identity_id": "33333333-3333-3333-3333-333333333333",
       *             "id": "<ID>",
       *             "user_id": "<USER_ID>",
       *             "identity_data": {
       *               "email": "example@email.com",
       *               "email_verified": true,
       *               "full_name": "User Name",
       *               "iss": "<ISS>",
       *               "name": "User Name",
       *               "phone_verified": false,
       *               "provider_id": "<PROVIDER_ID>",
       *               "sub": "<SUB>"
       *             },
       *             "provider": "<PROVIDER>",
       *             "last_sign_in_at": "2024-01-01T00:00:00Z",
       *             "created_at": "2024-01-01T00:00:00Z",
       *             "updated_at": "2024-01-01T00:00:00Z",
       *             "email": "example@email.com"
       *           }
       *         ],
       *         created_at: '2024-01-01T00:00:00Z',
       *         updated_at: '2024-01-01T00:00:00Z',
       *         is_anonymous: false
       *       },
       *       provider_token: '<PROVIDER_TOKEN>',
       *       provider_refresh_token: '<PROVIDER_REFRESH_TOKEN>'
       *     },
       *     user: {
       *       id: '11111111-1111-1111-1111-111111111111',
       *       aud: 'authenticated',
       *       role: 'authenticated',
       *       email: 'example@email.com',
       *       email_confirmed_at: '2024-01-01T00:00:00Z',
       *       phone: '',
       *       confirmation_sent_at: '2024-01-01T00:00:00Z',
       *       confirmed_at: '2024-01-01T00:00:00Z',
       *       last_sign_in_at: '2024-01-01T00:00:00Z',
       *       app_metadata: {
       *         provider: 'email',
       *         providers: [
       *           "email",
       *           "<OTHER_PROVIDER>"
       *         ]
       *       },
       *       user_metadata: {
       *         email: 'email@email.com',
       *         email_verified: true,
       *         full_name: 'User Name',
       *         iss: '<ISS>',
       *         name: 'User Name',
       *         phone_verified: false,
       *         provider_id: '<PROVIDER_ID>',
       *         sub: '<SUB>'
       *       },
       *       identities: [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "id": "11111111-1111-1111-1111-111111111111",
       *           "user_id": "11111111-1111-1111-1111-111111111111",
       *           "identity_data": {
       *             "email": "example@email.com",
       *             "email_verified": false,
       *             "phone_verified": false,
       *             "sub": "11111111-1111-1111-1111-111111111111"
       *           },
       *           "provider": "email",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "email@example.com"
       *         },
       *         {
       *           "identity_id": "33333333-3333-3333-3333-333333333333",
       *           "id": "<ID>",
       *           "user_id": "<USER_ID>",
       *           "identity_data": {
       *             "email": "example@email.com",
       *             "email_verified": true,
       *             "full_name": "User Name",
       *             "iss": "<ISS>",
       *             "name": "User Name",
       *             "phone_verified": false,
       *             "provider_id": "<PROVIDER_ID>",
       *             "sub": "<SUB>"
       *           },
       *           "provider": "<PROVIDER>",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "example@email.com"
       *         }
       *       ],
       *       created_at: '2024-01-01T00:00:00Z',
       *       updated_at: '2024-01-01T00:00:00Z',
       *       is_anonymous: false
       *     },
       *     redirectType: null
       *   },
       *   "error": null
       * }
       * ```
       */
      async exchangeCodeForSession(authCode) {
        await this.initializePromise;
        return this._acquireLock(this.lockAcquireTimeout, async () => {
          return this._exchangeCodeForSession(authCode);
        });
      }
      /**
       * Signs in a user by verifying a message signed by the user's private key.
       * Supports Ethereum (via Sign-In-With-Ethereum) & Solana (Sign-In-With-Solana) standards,
       * both of which derive from the EIP-4361 standard
       * With slight variation on Solana's side.
       * @reference https://eips.ethereum.org/EIPS/eip-4361
       *
       * @category Auth
       *
       * @remarks
       * - Uses a Web3 (Ethereum, Solana) wallet to sign a user in.
       * - Read up on the [potential for abuse](/docs/guides/auth/auth-web3#potential-for-abuse) before using it.
       *
       * @example Sign in with Solana or Ethereum (Window API)
       * ```js
       *   // uses window.ethereum for the wallet
       *   const { data, error } = await supabase.auth.signInWithWeb3({
       *     chain: 'ethereum',
       *     statement: 'I accept the Terms of Service at https://example.com/tos'
       *   })
       *
       *   // uses window.solana for the wallet
       *   const { data, error } = await supabase.auth.signInWithWeb3({
       *     chain: 'solana',
       *     statement: 'I accept the Terms of Service at https://example.com/tos'
       *   })
       * ```
       *
       * @example Sign in with Ethereum (Message and Signature)
       * ```js
       *   const { data, error } = await supabase.auth.signInWithWeb3({
       *     chain: 'ethereum',
       *     message: '<sign in with ethereum message>',
       *     signature: '<hex of the ethereum signature over the message>',
       *   })
       * ```
       *
       * @example Sign in with Solana (Brave)
       * ```js
       *   const { data, error } = await supabase.auth.signInWithWeb3({
       *     chain: 'solana',
       *     statement: 'I accept the Terms of Service at https://example.com/tos',
       *     wallet: window.braveSolana
       *   })
       * ```
       *
       * @example Sign in with Solana (Wallet Adapter)
       * ```jsx
       *   function SignInButton() {
       *   const wallet = useWallet()
       *
       *   return (
       *     <>
       *       {wallet.connected ? (
       *         <button
       *           onClick={() => {
       *             supabase.auth.signInWithWeb3({
       *               chain: 'solana',
       *               statement: 'I accept the Terms of Service at https://example.com/tos',
       *               wallet,
       *             })
       *           }}
       *         >
       *           Sign in with Solana
       *         </button>
       *       ) : (
       *         <WalletMultiButton />
       *       )}
       *     </>
       *   )
       * }
       *
       * function App() {
       *   const endpoint = clusterApiUrl('devnet')
       *   const wallets = useMemo(() => [], [])
       *
       *   return (
       *     <ConnectionProvider endpoint={endpoint}>
       *       <WalletProvider wallets={wallets}>
       *         <WalletModalProvider>
       *           <SignInButton />
       *         </WalletModalProvider>
       *       </WalletProvider>
       *     </ConnectionProvider>
       *   )
       * }
       * ```
       */
      async signInWithWeb3(credentials) {
        const { chain } = credentials;
        switch (chain) {
          case "ethereum":
            return await this.signInWithEthereum(credentials);
          case "solana":
            return await this.signInWithSolana(credentials);
          default:
            throw new Error(`@supabase/auth-js: Unsupported chain "${chain}"`);
        }
      }
      async signInWithEthereum(credentials) {
        var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l;
        let message;
        let signature;
        if ("message" in credentials) {
          message = credentials.message;
          signature = credentials.signature;
        } else {
          const { chain, wallet, statement, options } = credentials;
          let resolvedWallet;
          if (!(0, helpers_1.isBrowser)()) {
            if (typeof wallet !== "object" || !(options === null || options === void 0 ? void 0 : options.url)) {
              throw new Error("@supabase/auth-js: Both wallet and url must be specified in non-browser environments.");
            }
            resolvedWallet = wallet;
          } else if (typeof wallet === "object") {
            resolvedWallet = wallet;
          } else {
            const windowAny = window;
            if ("ethereum" in windowAny && typeof windowAny.ethereum === "object" && "request" in windowAny.ethereum && typeof windowAny.ethereum.request === "function") {
              resolvedWallet = windowAny.ethereum;
            } else {
              throw new Error(`@supabase/auth-js: No compatible Ethereum wallet interface on the window object (window.ethereum) detected. Make sure the user already has a wallet installed and connected for this app. Prefer passing the wallet interface object directly to signInWithWeb3({ chain: 'ethereum', wallet: resolvedUserWallet }) instead.`);
            }
          }
          const url = new URL((_a = options === null || options === void 0 ? void 0 : options.url) !== null && _a !== void 0 ? _a : window.location.href);
          const accounts = await resolvedWallet.request({
            method: "eth_requestAccounts"
          }).then((accs) => accs).catch(() => {
            throw new Error(`@supabase/auth-js: Wallet method eth_requestAccounts is missing or invalid`);
          });
          if (!accounts || accounts.length === 0) {
            throw new Error(`@supabase/auth-js: No accounts available. Please ensure the wallet is connected.`);
          }
          const address = (0, ethereum_1.getAddress)(accounts[0]);
          let chainId = (_b = options === null || options === void 0 ? void 0 : options.signInWithEthereum) === null || _b === void 0 ? void 0 : _b.chainId;
          if (!chainId) {
            const chainIdHex = await resolvedWallet.request({
              method: "eth_chainId"
            });
            chainId = (0, ethereum_1.fromHex)(chainIdHex);
          }
          const siweMessage = {
            domain: url.host,
            address,
            statement,
            uri: url.href,
            version: "1",
            chainId,
            nonce: (_c = options === null || options === void 0 ? void 0 : options.signInWithEthereum) === null || _c === void 0 ? void 0 : _c.nonce,
            issuedAt: (_e = (_d = options === null || options === void 0 ? void 0 : options.signInWithEthereum) === null || _d === void 0 ? void 0 : _d.issuedAt) !== null && _e !== void 0 ? _e : /* @__PURE__ */ new Date(),
            expirationTime: (_f = options === null || options === void 0 ? void 0 : options.signInWithEthereum) === null || _f === void 0 ? void 0 : _f.expirationTime,
            notBefore: (_g = options === null || options === void 0 ? void 0 : options.signInWithEthereum) === null || _g === void 0 ? void 0 : _g.notBefore,
            requestId: (_h = options === null || options === void 0 ? void 0 : options.signInWithEthereum) === null || _h === void 0 ? void 0 : _h.requestId,
            resources: (_j = options === null || options === void 0 ? void 0 : options.signInWithEthereum) === null || _j === void 0 ? void 0 : _j.resources
          };
          message = (0, ethereum_1.createSiweMessage)(siweMessage);
          signature = await resolvedWallet.request({
            method: "personal_sign",
            params: [(0, ethereum_1.toHex)(message), address]
          });
        }
        try {
          const { data, error } = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/token?grant_type=web3`, {
            headers: this.headers,
            body: Object.assign({
              chain: "ethereum",
              message,
              signature
            }, ((_k = credentials.options) === null || _k === void 0 ? void 0 : _k.captchaToken) ? { gotrue_meta_security: { captcha_token: (_l = credentials.options) === null || _l === void 0 ? void 0 : _l.captchaToken } } : null),
            xform: fetch_1._sessionResponse
          });
          if (error) {
            throw error;
          }
          if (!data || !data.session || !data.user) {
            const invalidTokenError = new errors_1.AuthInvalidTokenResponseError();
            return this._returnResult({ data: { user: null, session: null }, error: invalidTokenError });
          }
          if (data.session) {
            await this._saveSession(data.session);
            await this._notifyAllSubscribers("SIGNED_IN", data.session);
          }
          return this._returnResult({ data: Object.assign({}, data), error });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          throw error;
        }
      }
      async signInWithSolana(credentials) {
        var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l, _m;
        let message;
        let signature;
        if ("message" in credentials) {
          message = credentials.message;
          signature = credentials.signature;
        } else {
          const { chain, wallet, statement, options } = credentials;
          let resolvedWallet;
          if (!(0, helpers_1.isBrowser)()) {
            if (typeof wallet !== "object" || !(options === null || options === void 0 ? void 0 : options.url)) {
              throw new Error("@supabase/auth-js: Both wallet and url must be specified in non-browser environments.");
            }
            resolvedWallet = wallet;
          } else if (typeof wallet === "object") {
            resolvedWallet = wallet;
          } else {
            const windowAny = window;
            if ("solana" in windowAny && typeof windowAny.solana === "object" && ("signIn" in windowAny.solana && typeof windowAny.solana.signIn === "function" || "signMessage" in windowAny.solana && typeof windowAny.solana.signMessage === "function")) {
              resolvedWallet = windowAny.solana;
            } else {
              throw new Error(`@supabase/auth-js: No compatible Solana wallet interface on the window object (window.solana) detected. Make sure the user already has a wallet installed and connected for this app. Prefer passing the wallet interface object directly to signInWithWeb3({ chain: 'solana', wallet: resolvedUserWallet }) instead.`);
            }
          }
          const url = new URL((_a = options === null || options === void 0 ? void 0 : options.url) !== null && _a !== void 0 ? _a : window.location.href);
          if ("signIn" in resolvedWallet && resolvedWallet.signIn) {
            const output = await resolvedWallet.signIn(Object.assign(Object.assign(Object.assign({ issuedAt: (/* @__PURE__ */ new Date()).toISOString() }, options === null || options === void 0 ? void 0 : options.signInWithSolana), {
              // non-overridable properties
              version: "1",
              domain: url.host,
              uri: url.href
            }), statement ? { statement } : null));
            let outputToProcess;
            if (Array.isArray(output) && output[0] && typeof output[0] === "object") {
              outputToProcess = output[0];
            } else if (output && typeof output === "object" && "signedMessage" in output && "signature" in output) {
              outputToProcess = output;
            } else {
              throw new Error("@supabase/auth-js: Wallet method signIn() returned unrecognized value");
            }
            if ("signedMessage" in outputToProcess && "signature" in outputToProcess && (typeof outputToProcess.signedMessage === "string" || outputToProcess.signedMessage instanceof Uint8Array) && outputToProcess.signature instanceof Uint8Array) {
              message = typeof outputToProcess.signedMessage === "string" ? outputToProcess.signedMessage : new TextDecoder().decode(outputToProcess.signedMessage);
              signature = outputToProcess.signature;
            } else {
              throw new Error("@supabase/auth-js: Wallet method signIn() API returned object without signedMessage and signature fields");
            }
          } else {
            if (!("signMessage" in resolvedWallet) || typeof resolvedWallet.signMessage !== "function" || !("publicKey" in resolvedWallet) || typeof resolvedWallet !== "object" || !resolvedWallet.publicKey || !("toBase58" in resolvedWallet.publicKey) || typeof resolvedWallet.publicKey.toBase58 !== "function") {
              throw new Error("@supabase/auth-js: Wallet does not have a compatible signMessage() and publicKey.toBase58() API");
            }
            message = [
              `${url.host} wants you to sign in with your Solana account:`,
              resolvedWallet.publicKey.toBase58(),
              ...statement ? ["", statement, ""] : [""],
              "Version: 1",
              `URI: ${url.href}`,
              `Issued At: ${(_c = (_b = options === null || options === void 0 ? void 0 : options.signInWithSolana) === null || _b === void 0 ? void 0 : _b.issuedAt) !== null && _c !== void 0 ? _c : (/* @__PURE__ */ new Date()).toISOString()}`,
              ...((_d = options === null || options === void 0 ? void 0 : options.signInWithSolana) === null || _d === void 0 ? void 0 : _d.notBefore) ? [`Not Before: ${options.signInWithSolana.notBefore}`] : [],
              ...((_e = options === null || options === void 0 ? void 0 : options.signInWithSolana) === null || _e === void 0 ? void 0 : _e.expirationTime) ? [`Expiration Time: ${options.signInWithSolana.expirationTime}`] : [],
              ...((_f = options === null || options === void 0 ? void 0 : options.signInWithSolana) === null || _f === void 0 ? void 0 : _f.chainId) ? [`Chain ID: ${options.signInWithSolana.chainId}`] : [],
              ...((_g = options === null || options === void 0 ? void 0 : options.signInWithSolana) === null || _g === void 0 ? void 0 : _g.nonce) ? [`Nonce: ${options.signInWithSolana.nonce}`] : [],
              ...((_h = options === null || options === void 0 ? void 0 : options.signInWithSolana) === null || _h === void 0 ? void 0 : _h.requestId) ? [`Request ID: ${options.signInWithSolana.requestId}`] : [],
              ...((_k = (_j = options === null || options === void 0 ? void 0 : options.signInWithSolana) === null || _j === void 0 ? void 0 : _j.resources) === null || _k === void 0 ? void 0 : _k.length) ? [
                "Resources",
                ...options.signInWithSolana.resources.map((resource) => `- ${resource}`)
              ] : []
            ].join("\n");
            const maybeSignature = await resolvedWallet.signMessage(new TextEncoder().encode(message), "utf8");
            if (!maybeSignature || !(maybeSignature instanceof Uint8Array)) {
              throw new Error("@supabase/auth-js: Wallet signMessage() API returned an recognized value");
            }
            signature = maybeSignature;
          }
        }
        try {
          const { data, error } = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/token?grant_type=web3`, {
            headers: this.headers,
            body: Object.assign({ chain: "solana", message, signature: (0, base64url_1.bytesToBase64URL)(signature) }, ((_l = credentials.options) === null || _l === void 0 ? void 0 : _l.captchaToken) ? { gotrue_meta_security: { captcha_token: (_m = credentials.options) === null || _m === void 0 ? void 0 : _m.captchaToken } } : null),
            xform: fetch_1._sessionResponse
          });
          if (error) {
            throw error;
          }
          if (!data || !data.session || !data.user) {
            const invalidTokenError = new errors_1.AuthInvalidTokenResponseError();
            return this._returnResult({ data: { user: null, session: null }, error: invalidTokenError });
          }
          if (data.session) {
            await this._saveSession(data.session);
            await this._notifyAllSubscribers("SIGNED_IN", data.session);
          }
          return this._returnResult({ data: Object.assign({}, data), error });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          throw error;
        }
      }
      async _exchangeCodeForSession(authCode) {
        const storageItem = await (0, helpers_1.getItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
        const [codeVerifier, redirectType] = (storageItem !== null && storageItem !== void 0 ? storageItem : "").split("/");
        try {
          if (!codeVerifier && this.flowType === "pkce") {
            throw new errors_1.AuthPKCECodeVerifierMissingError();
          }
          const { data, error } = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/token?grant_type=pkce`, {
            headers: this.headers,
            body: {
              auth_code: authCode,
              code_verifier: codeVerifier
            },
            xform: fetch_1._sessionResponse
          });
          await (0, helpers_1.removeItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
          if (error) {
            throw error;
          }
          if (!data || !data.session || !data.user) {
            const invalidTokenError = new errors_1.AuthInvalidTokenResponseError();
            return this._returnResult({
              data: { user: null, session: null, redirectType: null },
              error: invalidTokenError
            });
          }
          if (data.session) {
            await this._saveSession(data.session);
            await this._notifyAllSubscribers(redirectType === "recovery" ? "PASSWORD_RECOVERY" : "SIGNED_IN", data.session);
          }
          return this._returnResult({ data: Object.assign(Object.assign({}, data), { redirectType: redirectType !== null && redirectType !== void 0 ? redirectType : null }), error });
        } catch (error) {
          await (0, helpers_1.removeItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({
              data: { user: null, session: null, redirectType: null },
              error
            });
          }
          throw error;
        }
      }
      /**
       * Allows signing in with an OIDC ID token. The authentication provider used
       * should be enabled and configured.
       *
       * @category Auth
       *
       * @remarks
       * - Use an ID token to sign in.
       * - Especially useful when implementing sign in using native platform dialogs in mobile or desktop apps using Sign in with Apple or Sign in with Google on iOS and Android.
       * - You can also use Google's [One Tap](https://developers.google.com/identity/gsi/web/guides/display-google-one-tap) and [Automatic sign-in](https://developers.google.com/identity/gsi/web/guides/automatic-sign-in-sign-out) via this API.
       *
       * @example Sign In using ID Token
       * ```js
       * const { data, error } = await supabase.auth.signInWithIdToken({
       *   provider: 'google',
       *   token: 'your-id-token'
       * })
       * ```
       *
       * @exampleResponse Sign In using ID Token
       * ```json
       * {
       *   "data": {
       *     "user": {
       *       "id": "11111111-1111-1111-1111-111111111111",
       *       "aud": "authenticated",
       *       "role": "authenticated",
       *       "last_sign_in_at": "2024-01-01T00:00:00Z",
       *       "app_metadata": {
       *         ...
       *       },
       *       "user_metadata": {
       *         ...
       *       },
       *       "identities": [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "provider": "google",
       *         }
       *       ],
       *       "created_at": "2024-01-01T00:00:00Z",
       *       "updated_at": "2024-01-01T00:00:00Z",
       *     },
       *     "session": {
       *       "access_token": "<ACCESS_TOKEN>",
       *       "token_type": "bearer",
       *       "expires_in": 3600,
       *       "expires_at": 1700000000,
       *       "refresh_token": "<REFRESH_TOKEN>",
       *       "user": {
       *         "id": "11111111-1111-1111-1111-111111111111",
       *         "aud": "authenticated",
       *         "role": "authenticated",
       *         "last_sign_in_at": "2024-01-01T00:00:00Z",
       *         "app_metadata": {
       *           ...
       *         },
       *         "user_metadata": {
       *           ...
       *         },
       *         "identities": [
       *           {
       *             "identity_id": "22222222-2222-2222-2222-222222222222",
       *             "provider": "google",
       *           }
       *         ],
       *         "created_at": "2024-01-01T00:00:00Z",
       *         "updated_at": "2024-01-01T00:00:00Z",
       *       }
       *     }
       *   },
       *   "error": null
       * }
       * ```
       */
      async signInWithIdToken(credentials) {
        try {
          const { options, provider, token, access_token, nonce } = credentials;
          const res = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/token?grant_type=id_token`, {
            headers: this.headers,
            body: {
              provider,
              id_token: token,
              access_token,
              nonce,
              gotrue_meta_security: { captcha_token: options === null || options === void 0 ? void 0 : options.captchaToken }
            },
            xform: fetch_1._sessionResponse
          });
          const { data, error } = res;
          if (error) {
            return this._returnResult({ data: { user: null, session: null }, error });
          } else if (!data || !data.session || !data.user) {
            const invalidTokenError = new errors_1.AuthInvalidTokenResponseError();
            return this._returnResult({ data: { user: null, session: null }, error: invalidTokenError });
          }
          if (data.session) {
            await this._saveSession(data.session);
            await this._notifyAllSubscribers("SIGNED_IN", data.session);
          }
          return this._returnResult({ data, error });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          throw error;
        }
      }
      /**
       * Log in a user using magiclink or a one-time password (OTP).
       *
       * If the `{{ .ConfirmationURL }}` variable is specified in the email template, a magiclink will be sent.
       * If the `{{ .Token }}` variable is specified in the email template, an OTP will be sent.
       * If you're using phone sign-ins, only an OTP will be sent. You won't be able to send a magiclink for phone sign-ins.
       *
       * Be aware that you may get back an error message that will not distinguish
       * between the cases where the account does not exist or, that the account
       * can only be accessed via social login.
       *
       * Do note that you will need to configure a Whatsapp sender on Twilio
       * if you are using phone sign in with the 'whatsapp' channel. The whatsapp
       * channel is not supported on other providers
       * at this time.
       * This method supports PKCE when an email is passed.
       *
       * @category Auth
       *
       * @remarks
       * - Requires either an email or phone number.
       * - This method is used for passwordless sign-ins where a OTP is sent to the user's email or phone number.
       * - If the user doesn't exist, `signInWithOtp()` will signup the user instead. To restrict this behavior, you can set `shouldCreateUser` in `SignInWithPasswordlessCredentials.options` to `false`.
       * - If you're using an email, you can configure whether you want the user to receive a magiclink or a OTP.
       * - If you're using phone, you can configure whether you want the user to receive a OTP.
       * - The magic link's destination URL is determined by the [`SITE_URL`](/docs/guides/auth/redirect-urls#use-wildcards-in-redirect-urls).
       * - See [redirect URLs and wildcards](/docs/guides/auth/redirect-urls#use-wildcards-in-redirect-urls) to add additional redirect URLs to your project.
       * - Magic links and OTPs share the same implementation. To send users a one-time code instead of a magic link, [modify the magic link email template](/dashboard/project/_/auth/templates) to include `{{ .Token }}` instead of `{{ .ConfirmationURL }}`.
       * - See our [Twilio Phone Auth Guide](/docs/guides/auth/phone-login?showSMSProvider=Twilio) for details about configuring WhatsApp sign in.
       *
       * @exampleDescription Sign in with email
       * The user will be sent an email which contains either a magiclink or a OTP or both. By default, a given user can only request a OTP once every 60 seconds.
       *
       * @example Sign in with email
       * ```js
       * const { data, error } = await supabase.auth.signInWithOtp({
       *   email: 'example@email.com',
       *   options: {
       *     emailRedirectTo: 'https://example.com/welcome'
       *   }
       * })
       * ```
       *
       * @exampleResponse Sign in with email
       * ```json
       * {
       *   "data": {
       *     "user": null,
       *     "session": null
       *   },
       *   "error": null
       * }
       * ```
       *
       * @exampleDescription Sign in with SMS OTP
       * The user will be sent a SMS which contains a OTP. By default, a given user can only request a OTP once every 60 seconds.
       *
       * @example Sign in with SMS OTP
       * ```js
       * const { data, error } = await supabase.auth.signInWithOtp({
       *   phone: '+13334445555',
       * })
       * ```
       *
       * @exampleDescription Sign in with WhatsApp OTP
       * The user will be sent a WhatsApp message which contains a OTP. By default, a given user can only request a OTP once every 60 seconds. Note that a user will need to have a valid WhatsApp account that is linked to Twilio in order to use this feature.
       *
       * @example Sign in with WhatsApp OTP
       * ```js
       * const { data, error } = await supabase.auth.signInWithOtp({
       *   phone: '+13334445555',
       *   options: {
       *     channel:'whatsapp',
       *   }
       * })
       * ```
       */
      async signInWithOtp(credentials) {
        var _a, _b, _c, _d, _e;
        try {
          if ("email" in credentials) {
            const { email, options } = credentials;
            let codeChallenge = null;
            let codeChallengeMethod = null;
            if (this.flowType === "pkce") {
              ;
              [codeChallenge, codeChallengeMethod] = await (0, helpers_1.getCodeChallengeAndMethod)(this.storage, this.storageKey);
            }
            const { error } = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/otp`, {
              headers: this.headers,
              body: {
                email,
                data: (_a = options === null || options === void 0 ? void 0 : options.data) !== null && _a !== void 0 ? _a : {},
                create_user: (_b = options === null || options === void 0 ? void 0 : options.shouldCreateUser) !== null && _b !== void 0 ? _b : true,
                gotrue_meta_security: { captcha_token: options === null || options === void 0 ? void 0 : options.captchaToken },
                code_challenge: codeChallenge,
                code_challenge_method: codeChallengeMethod
              },
              redirectTo: options === null || options === void 0 ? void 0 : options.emailRedirectTo
            });
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          if ("phone" in credentials) {
            const { phone, options } = credentials;
            const { data, error } = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/otp`, {
              headers: this.headers,
              body: {
                phone,
                data: (_c = options === null || options === void 0 ? void 0 : options.data) !== null && _c !== void 0 ? _c : {},
                create_user: (_d = options === null || options === void 0 ? void 0 : options.shouldCreateUser) !== null && _d !== void 0 ? _d : true,
                gotrue_meta_security: { captcha_token: options === null || options === void 0 ? void 0 : options.captchaToken },
                channel: (_e = options === null || options === void 0 ? void 0 : options.channel) !== null && _e !== void 0 ? _e : "sms"
              }
            });
            return this._returnResult({
              data: { user: null, session: null, messageId: data === null || data === void 0 ? void 0 : data.message_id },
              error
            });
          }
          throw new errors_1.AuthInvalidCredentialsError("You must provide either an email or phone number.");
        } catch (error) {
          await (0, helpers_1.removeItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          throw error;
        }
      }
      /**
       * Log in a user given a User supplied OTP or TokenHash received through mobile or email.
       *
       * @category Auth
       *
       * @remarks
       * - The `verifyOtp` method takes in different verification types.
       * - If a phone number is used, the type can either be:
       *   1. `sms` – Used when verifying a one-time password (OTP) sent via SMS during sign-up or sign-in.
       *   2. `phone_change` – Used when verifying an OTP sent to a new phone number during a phone number update process.
       * - If an email address is used, the type can be one of the following (note: `signup` and `magiclink` types are deprecated):
       *   1. `email` – Used when verifying an OTP sent to the user's email during sign-up or sign-in.
       *   2. `recovery` – Used when verifying an OTP sent for account recovery, typically after a password reset request.
       *   3. `invite` – Used when verifying an OTP sent as part of an invitation to join a project or organization.
       *   4. `email_change` – Used when verifying an OTP sent to a new email address during an email update process.
       * - The verification type used should be determined based on the corresponding auth method called before `verifyOtp` to sign up / sign-in a user.
       * - The `TokenHash` is contained in the [email templates](/docs/guides/auth/auth-email-templates) and can be used to sign in.  You may wish to use the hash for the PKCE flow for Server Side Auth. Read [the Password-based Auth guide](/docs/guides/auth/passwords) for more details.
       *
       * @example Verify Signup One-Time Password (OTP)
       * ```js
       * const { data, error } = await supabase.auth.verifyOtp({ email, token, type: 'email'})
       * ```
       *
       * @exampleResponse Verify Signup One-Time Password (OTP)
       * ```json
       * {
       *   "data": {
       *     "user": {
       *       "id": "11111111-1111-1111-1111-111111111111",
       *       "aud": "authenticated",
       *       "role": "authenticated",
       *       "email": "example@email.com",
       *       "email_confirmed_at": "2024-01-01T00:00:00Z",
       *       "phone": "",
       *       "confirmed_at": "2024-01-01T00:00:00Z",
       *       "recovery_sent_at": "2024-01-01T00:00:00Z",
       *       "last_sign_in_at": "2024-01-01T00:00:00Z",
       *       "app_metadata": {
       *         "provider": "email",
       *         "providers": [
       *           "email"
       *         ]
       *       },
       *       "user_metadata": {
       *         "email": "example@email.com",
       *         "email_verified": false,
       *         "phone_verified": false,
       *         "sub": "11111111-1111-1111-1111-111111111111"
       *       },
       *       "identities": [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "id": "11111111-1111-1111-1111-111111111111",
       *           "user_id": "11111111-1111-1111-1111-111111111111",
       *           "identity_data": {
       *             "email": "example@email.com",
       *             "email_verified": false,
       *             "phone_verified": false,
       *             "sub": "11111111-1111-1111-1111-111111111111"
       *           },
       *           "provider": "email",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "example@email.com"
       *         }
       *       ],
       *       "created_at": "2024-01-01T00:00:00Z",
       *       "updated_at": "2024-01-01T00:00:00Z",
       *       "is_anonymous": false
       *     },
       *     "session": {
       *       "access_token": "<ACCESS_TOKEN>",
       *       "token_type": "bearer",
       *       "expires_in": 3600,
       *       "expires_at": 1700000000,
       *       "refresh_token": "<REFRESH_TOKEN>",
       *       "user": {
       *         "id": "11111111-1111-1111-1111-111111111111",
       *         "aud": "authenticated",
       *         "role": "authenticated",
       *         "email": "example@email.com",
       *         "email_confirmed_at": "2024-01-01T00:00:00Z",
       *         "phone": "",
       *         "confirmed_at": "2024-01-01T00:00:00Z",
       *         "recovery_sent_at": "2024-01-01T00:00:00Z",
       *         "last_sign_in_at": "2024-01-01T00:00:00Z",
       *         "app_metadata": {
       *           "provider": "email",
       *           "providers": [
       *             "email"
       *           ]
       *         },
       *         "user_metadata": {
       *           "email": "example@email.com",
       *           "email_verified": false,
       *           "phone_verified": false,
       *           "sub": "11111111-1111-1111-1111-111111111111"
       *         },
       *         "identities": [
       *           {
       *             "identity_id": "22222222-2222-2222-2222-222222222222",
       *             "id": "11111111-1111-1111-1111-111111111111",
       *             "user_id": "11111111-1111-1111-1111-111111111111",
       *             "identity_data": {
       *               "email": "example@email.com",
       *               "email_verified": false,
       *               "phone_verified": false,
       *               "sub": "11111111-1111-1111-1111-111111111111"
       *             },
       *             "provider": "email",
       *             "last_sign_in_at": "2024-01-01T00:00:00Z",
       *             "created_at": "2024-01-01T00:00:00Z",
       *             "updated_at": "2024-01-01T00:00:00Z",
       *             "email": "example@email.com"
       *           }
       *         ],
       *         "created_at": "2024-01-01T00:00:00Z",
       *         "updated_at": "2024-01-01T00:00:00Z",
       *         "is_anonymous": false
       *       }
       *     }
       *   },
       *   "error": null
       * }
       * ```
       *
       * @example Verify SMS One-Time Password (OTP)
       * ```js
       * const { data, error } = await supabase.auth.verifyOtp({ phone, token, type: 'sms'})
       * ```
       *
       * @example Verify Email Auth (Token Hash)
       * ```js
       * const { data, error } = await supabase.auth.verifyOtp({ token_hash: tokenHash, type: 'email'})
       * ```
       */
      async verifyOtp(params) {
        var _a, _b;
        try {
          let redirectTo = void 0;
          let captchaToken = void 0;
          if ("options" in params) {
            redirectTo = (_a = params.options) === null || _a === void 0 ? void 0 : _a.redirectTo;
            captchaToken = (_b = params.options) === null || _b === void 0 ? void 0 : _b.captchaToken;
          }
          const { data, error } = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/verify`, {
            headers: this.headers,
            body: Object.assign(Object.assign({}, params), { gotrue_meta_security: { captcha_token: captchaToken } }),
            redirectTo,
            xform: fetch_1._sessionResponse
          });
          if (error) {
            throw error;
          }
          if (!data) {
            const tokenVerificationError = new Error("An error occurred on token verification.");
            throw tokenVerificationError;
          }
          const session = data.session;
          const user = data.user;
          if (session === null || session === void 0 ? void 0 : session.access_token) {
            await this._saveSession(session);
            await this._notifyAllSubscribers(params.type == "recovery" ? "PASSWORD_RECOVERY" : "SIGNED_IN", session);
          }
          return this._returnResult({ data: { user, session }, error: null });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          throw error;
        }
      }
      /**
       * Attempts a single-sign on using an enterprise Identity Provider. A
       * successful SSO attempt will redirect the current page to the identity
       * provider authorization page. The redirect URL is implementation and SSO
       * protocol specific.
       *
       * You can use it by providing a SSO domain. Typically you can extract this
       * domain by asking users for their email address. If this domain is
       * registered on the Auth instance the redirect will use that organization's
       * currently active SSO Identity Provider for the login.
       *
       * If you have built an organization-specific login page, you can use the
       * organization's SSO Identity Provider UUID directly instead.
       *
       * @category Auth
       *
       * @remarks
       * - Before you can call this method you need to [establish a connection](/docs/guides/auth/sso/auth-sso-saml#managing-saml-20-connections) to an identity provider. Use the [CLI commands](/docs/reference/cli/supabase-sso) to do this.
       * - If you've associated an email domain to the identity provider, you can use the `domain` property to start a sign-in flow.
       * - In case you need to use a different way to start the authentication flow with an identity provider, you can use the `providerId` property. For example:
       *     - Mapping specific user email addresses with an identity provider.
       *     - Using different hints to identity the identity provider to be used by the user, like a company-specific page, IP address or other tracking information.
       *
       * @example Sign in with email domain
       * ```js
       *   // You can extract the user's email domain and use it to trigger the
       *   // authentication flow with the correct identity provider.
       *
       *   const { data, error } = await supabase.auth.signInWithSSO({
       *     domain: 'company.com'
       *   })
       *
       *   if (data?.url) {
       *     // redirect the user to the identity provider's authentication flow
       *     window.location.href = data.url
       *   }
       * ```
       *
       * @example Sign in with provider UUID
       * ```js
       *   // Useful when you need to map a user's sign in request according
       *   // to different rules that can't use email domains.
       *
       *   const { data, error } = await supabase.auth.signInWithSSO({
       *     providerId: '21648a9d-8d5a-4555-a9d1-d6375dc14e92'
       *   })
       *
       *   if (data?.url) {
       *     // redirect the user to the identity provider's authentication flow
       *     window.location.href = data.url
       *   }
       * ```
       */
      async signInWithSSO(params) {
        var _a, _b, _c, _d, _e;
        try {
          let codeChallenge = null;
          let codeChallengeMethod = null;
          if (this.flowType === "pkce") {
            ;
            [codeChallenge, codeChallengeMethod] = await (0, helpers_1.getCodeChallengeAndMethod)(this.storage, this.storageKey);
          }
          const result = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/sso`, {
            body: Object.assign(Object.assign(Object.assign(Object.assign(Object.assign({}, "providerId" in params ? { provider_id: params.providerId } : null), "domain" in params ? { domain: params.domain } : null), { redirect_to: (_b = (_a = params.options) === null || _a === void 0 ? void 0 : _a.redirectTo) !== null && _b !== void 0 ? _b : void 0 }), ((_c = params === null || params === void 0 ? void 0 : params.options) === null || _c === void 0 ? void 0 : _c.captchaToken) ? { gotrue_meta_security: { captcha_token: params.options.captchaToken } } : null), { skip_http_redirect: true, code_challenge: codeChallenge, code_challenge_method: codeChallengeMethod }),
            headers: this.headers,
            xform: fetch_1._ssoResponse
          });
          if (((_d = result.data) === null || _d === void 0 ? void 0 : _d.url) && (0, helpers_1.isBrowser)() && !((_e = params.options) === null || _e === void 0 ? void 0 : _e.skipBrowserRedirect)) {
            window.location.assign(result.data.url);
          }
          return this._returnResult(result);
        } catch (error) {
          await (0, helpers_1.removeItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: null, error });
          }
          throw error;
        }
      }
      /**
       * Sends a reauthentication OTP to the user's email or phone number.
       * Requires the user to be signed-in.
       *
       * @category Auth
       *
       * @remarks
       * - This method is used together with `updateUser()` when a user's password needs to be updated.
       * - If you require your user to reauthenticate before updating their password, you need to enable the **Secure password change** option in your [project's email provider settings](/dashboard/project/_/auth/providers).
       * - A user is only require to reauthenticate before updating their password if **Secure password change** is enabled and the user **hasn't recently signed in**. A user is deemed recently signed in if the session was created in the last 24 hours.
       * - This method will send a nonce to the user's email. If the user doesn't have a confirmed email address, the method will send the nonce to the user's confirmed phone number instead.
       * - After receiving the OTP, include it as the `nonce` in your `updateUser()` call to finalize the password change.
       *
       * @exampleDescription Send reauthentication nonce
       * Sends a reauthentication nonce to the user's email or phone number.
       *
       * @example Send reauthentication nonce
       * ```js
       * const { error } = await supabase.auth.reauthenticate()
       * ```
       */
      async reauthenticate() {
        await this.initializePromise;
        return await this._acquireLock(this.lockAcquireTimeout, async () => {
          return await this._reauthenticate();
        });
      }
      async _reauthenticate() {
        try {
          return await this._useSession(async (result) => {
            const { data: { session }, error: sessionError } = result;
            if (sessionError)
              throw sessionError;
            if (!session)
              throw new errors_1.AuthSessionMissingError();
            const { error } = await (0, fetch_1._request)(this.fetch, "GET", `${this.url}/reauthenticate`, {
              headers: this.headers,
              jwt: session.access_token
            });
            return this._returnResult({ data: { user: null, session: null }, error });
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          throw error;
        }
      }
      /**
       * Resends an existing signup confirmation email, email change email, SMS OTP or phone change OTP.
       *
       * @category Auth
       *
       * @remarks
       * - Resends a signup confirmation, email change or phone change email to the user.
       * - Passwordless sign-ins can be resent by calling the `signInWithOtp()` method again.
       * - Password recovery emails can be resent by calling the `resetPasswordForEmail()` method again.
       * - This method will only resend an email or phone OTP to the user if there was an initial signup, email change or phone change request being made(note: For existing users signing in with OTP, you should use `signInWithOtp()` again to resend the OTP).
       * - You can specify a redirect url when you resend an email link using the `emailRedirectTo` option.
       *
       * @exampleDescription Resend an email signup confirmation
       * Resends the email signup confirmation to the user
       *
       * @example Resend an email signup confirmation
       * ```js
       * const { error } = await supabase.auth.resend({
       *   type: 'signup',
       *   email: 'email@example.com',
       *   options: {
       *     emailRedirectTo: 'https://example.com/welcome'
       *   }
       * })
       * ```
       *
       * @exampleDescription Resend a phone signup confirmation
       * Resends the phone signup confirmation email to the user
       *
       * @example Resend a phone signup confirmation
       * ```js
       * const { error } = await supabase.auth.resend({
       *   type: 'sms',
       *   phone: '1234567890'
       * })
       * ```
       *
       * @exampleDescription Resend email change email
       * Resends the email change email to the user
       *
       * @example Resend email change email
       * ```js
       * const { error } = await supabase.auth.resend({
       *   type: 'email_change',
       *   email: 'email@example.com'
       * })
       * ```
       *
       * @exampleDescription Resend phone change OTP
       * Resends the phone change OTP to the user
       *
       * @example Resend phone change OTP
       * ```js
       * const { error } = await supabase.auth.resend({
       *   type: 'phone_change',
       *   phone: '1234567890'
       * })
       * ```
       */
      async resend(credentials) {
        try {
          const endpoint = `${this.url}/resend`;
          if ("email" in credentials) {
            const { email, type, options } = credentials;
            const { error } = await (0, fetch_1._request)(this.fetch, "POST", endpoint, {
              headers: this.headers,
              body: {
                email,
                type,
                gotrue_meta_security: { captcha_token: options === null || options === void 0 ? void 0 : options.captchaToken }
              },
              redirectTo: options === null || options === void 0 ? void 0 : options.emailRedirectTo
            });
            return this._returnResult({ data: { user: null, session: null }, error });
          } else if ("phone" in credentials) {
            const { phone, type, options } = credentials;
            const { data, error } = await (0, fetch_1._request)(this.fetch, "POST", endpoint, {
              headers: this.headers,
              body: {
                phone,
                type,
                gotrue_meta_security: { captcha_token: options === null || options === void 0 ? void 0 : options.captchaToken }
              }
            });
            return this._returnResult({
              data: { user: null, session: null, messageId: data === null || data === void 0 ? void 0 : data.message_id },
              error
            });
          }
          throw new errors_1.AuthInvalidCredentialsError("You must provide either an email or phone number and a type");
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          throw error;
        }
      }
      /**
       * Returns the session, refreshing it if necessary.
       *
       * The session returned can be null if the session is not detected which can happen in the event a user is not signed-in or has logged out.
       *
       * **IMPORTANT:** This method loads values directly from the storage attached
       * to the client. If that storage is based on request cookies for example,
       * the values in it may not be authentic and therefore it's strongly advised
       * against using this method and its results in such circumstances. A warning
       * will be emitted if this is detected. Use {@link #getUser()} instead.
       *
       * @category Auth
       *
       * @remarks
       * - Since the introduction of [asymmetric JWT signing keys](/docs/guides/auth/signing-keys), this method is considered low-level and we encourage you to use `getClaims()` or `getUser()` instead.
       * - Retrieves the current [user session](/docs/guides/auth/sessions) from the storage medium (local storage, cookies).
       * - The session contains an access token (signed JWT), a refresh token and the user object.
       * - If the session's access token is expired or is about to expire, this method will use the refresh token to refresh the session.
       * - When using in a browser, or you've called `startAutoRefresh()` in your environment (React Native, etc.) this function always returns a valid access token without refreshing the session itself, as this is done in the background. This function returns very fast.
       * - **IMPORTANT SECURITY NOTICE:** If using an insecure storage medium, such as cookies or request headers, the user object returned by this function **must not be trusted**. Always verify the JWT using `getClaims()` or your own JWT verification library to securely establish the user's identity and access. You can also use `getUser()` to fetch the user object directly from the Auth server for this purpose.
       * - When using in a browser, this function is synchronized across all tabs using the [LockManager](https://developer.mozilla.org/en-US/docs/Web/API/LockManager) API. In other environments make sure you've defined a proper `lock` property, if necessary, to make sure there are no race conditions while the session is being refreshed.
       *
       * @example Get the session data
       * ```js
       * const { data, error } = await supabase.auth.getSession()
       * ```
       *
       * @exampleResponse Get the session data
       * ```json
       * {
       *   "data": {
       *     "session": {
       *       "access_token": "<ACCESS_TOKEN>",
       *       "token_type": "bearer",
       *       "expires_in": 3600,
       *       "expires_at": 1700000000,
       *       "refresh_token": "<REFRESH_TOKEN>",
       *       "user": {
       *         "id": "11111111-1111-1111-1111-111111111111",
       *         "aud": "authenticated",
       *         "role": "authenticated",
       *         "email": "example@email.com",
       *         "email_confirmed_at": "2024-01-01T00:00:00Z",
       *         "phone": "",
       *         "last_sign_in_at": "2024-01-01T00:00:00Z",
       *         "app_metadata": {
       *           "provider": "email",
       *           "providers": [
       *             "email"
       *           ]
       *         },
       *         "user_metadata": {
       *           "email": "example@email.com",
       *           "email_verified": false,
       *           "phone_verified": false,
       *           "sub": "11111111-1111-1111-1111-111111111111"
       *         },
       *         "identities": [
       *           {
       *             "identity_id": "22222222-2222-2222-2222-222222222222",
       *             "id": "11111111-1111-1111-1111-111111111111",
       *             "user_id": "11111111-1111-1111-1111-111111111111",
       *             "identity_data": {
       *               "email": "example@email.com",
       *               "email_verified": false,
       *               "phone_verified": false,
       *               "sub": "11111111-1111-1111-1111-111111111111"
       *             },
       *             "provider": "email",
       *             "last_sign_in_at": "2024-01-01T00:00:00Z",
       *             "created_at": "2024-01-01T00:00:00Z",
       *             "updated_at": "2024-01-01T00:00:00Z",
       *             "email": "example@email.com"
       *           }
       *         ],
       *         "created_at": "2024-01-01T00:00:00Z",
       *         "updated_at": "2024-01-01T00:00:00Z",
       *         "is_anonymous": false
       *       }
       *     }
       *   },
       *   "error": null
       * }
       * ```
       */
      async getSession() {
        await this.initializePromise;
        const result = await this._acquireLock(this.lockAcquireTimeout, async () => {
          return this._useSession(async (result2) => {
            return result2;
          });
        });
        return result;
      }
      /**
       * Acquires a global lock based on the storage key.
       */
      async _acquireLock(acquireTimeout, fn) {
        this._debug("#_acquireLock", "begin", acquireTimeout);
        try {
          if (this.lockAcquired) {
            const last = this.pendingInLock.length ? this.pendingInLock[this.pendingInLock.length - 1] : Promise.resolve();
            const result = (async () => {
              await last;
              return await fn();
            })();
            this.pendingInLock.push((async () => {
              try {
                await result;
              } catch (e) {
              }
            })());
            return result;
          }
          return await this.lock(`lock:${this.storageKey}`, acquireTimeout, async () => {
            this._debug("#_acquireLock", "lock acquired for storage key", this.storageKey);
            try {
              this.lockAcquired = true;
              const result = fn();
              this.pendingInLock.push((async () => {
                try {
                  await result;
                } catch (e) {
                }
              })());
              await result;
              while (this.pendingInLock.length) {
                const waitOn = [...this.pendingInLock];
                await Promise.all(waitOn);
                this.pendingInLock.splice(0, waitOn.length);
              }
              return await result;
            } finally {
              this._debug("#_acquireLock", "lock released for storage key", this.storageKey);
              this.lockAcquired = false;
            }
          });
        } finally {
          this._debug("#_acquireLock", "end");
        }
      }
      /**
       * Use instead of {@link #getSession} inside the library. It is
       * semantically usually what you want, as getting a session involves some
       * processing afterwards that requires only one client operating on the
       * session at once across multiple tabs or processes.
       */
      async _useSession(fn) {
        this._debug("#_useSession", "begin");
        try {
          const result = await this.__loadSession();
          return await fn(result);
        } finally {
          this._debug("#_useSession", "end");
        }
      }
      /**
       * NEVER USE DIRECTLY!
       *
       * Always use {@link #_useSession}.
       */
      async __loadSession() {
        this._debug("#__loadSession()", "begin");
        if (!this.lockAcquired) {
          this._debug("#__loadSession()", "used outside of an acquired lock!", new Error().stack);
        }
        try {
          let currentSession = null;
          const maybeSession = await (0, helpers_1.getItemAsync)(this.storage, this.storageKey);
          this._debug("#getSession()", "session from storage", maybeSession);
          if (maybeSession !== null) {
            if (this._isValidSession(maybeSession)) {
              currentSession = maybeSession;
            } else {
              this._debug("#getSession()", "session from storage is not valid");
              await this._removeSession();
            }
          }
          if (!currentSession) {
            return { data: { session: null }, error: null };
          }
          const hasExpired = currentSession.expires_at ? currentSession.expires_at * 1e3 - Date.now() < constants_1.EXPIRY_MARGIN_MS : false;
          this._debug("#__loadSession()", `session has${hasExpired ? "" : " not"} expired`, "expires_at", currentSession.expires_at);
          if (!hasExpired) {
            if (this.userStorage) {
              const maybeUser = await (0, helpers_1.getItemAsync)(this.userStorage, this.storageKey + "-user");
              if (maybeUser === null || maybeUser === void 0 ? void 0 : maybeUser.user) {
                currentSession.user = maybeUser.user;
              } else {
                currentSession.user = (0, helpers_1.userNotAvailableProxy)();
              }
            }
            if (this.storage.isServer && currentSession.user && !currentSession.user.__isUserNotAvailableProxy) {
              const suppressWarningRef = { value: this.suppressGetSessionWarning };
              currentSession.user = (0, helpers_1.insecureUserWarningProxy)(currentSession.user, suppressWarningRef);
              if (suppressWarningRef.value) {
                this.suppressGetSessionWarning = true;
              }
            }
            return { data: { session: currentSession }, error: null };
          }
          const { data: session, error } = await this._callRefreshToken(currentSession.refresh_token);
          if (error) {
            return this._returnResult({ data: { session: null }, error });
          }
          return this._returnResult({ data: { session }, error: null });
        } finally {
          this._debug("#__loadSession()", "end");
        }
      }
      /**
       * Gets the current user details if there is an existing session. This method
       * performs a network request to the Supabase Auth server, so the returned
       * value is authentic and can be used to base authorization rules on.
       *
       * @param jwt Takes in an optional access token JWT. If no JWT is provided, the JWT from the current session is used.
       *
       * @category Auth
       *
       * @remarks
       * - This method fetches the user object from the database instead of local session.
       * - This method is useful for checking if the user is authorized because it validates the user's access token JWT on the server.
       * - Should always be used when checking for user authorization on the server. On the client, you can instead use `getSession().session.user` for faster results. `getSession` is insecure on the server.
       *
       * @example Get the logged in user with the current existing session
       * ```js
       * const { data: { user } } = await supabase.auth.getUser()
       * ```
       *
       * @exampleResponse Get the logged in user with the current existing session
       * ```json
       * {
       *   "data": {
       *     "user": {
       *       "id": "11111111-1111-1111-1111-111111111111",
       *       "aud": "authenticated",
       *       "role": "authenticated",
       *       "email": "example@email.com",
       *       "email_confirmed_at": "2024-01-01T00:00:00Z",
       *       "phone": "",
       *       "confirmed_at": "2024-01-01T00:00:00Z",
       *       "last_sign_in_at": "2024-01-01T00:00:00Z",
       *       "app_metadata": {
       *         "provider": "email",
       *         "providers": [
       *           "email"
       *         ]
       *       },
       *       "user_metadata": {
       *         "email": "example@email.com",
       *         "email_verified": false,
       *         "phone_verified": false,
       *         "sub": "11111111-1111-1111-1111-111111111111"
       *       },
       *       "identities": [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "id": "11111111-1111-1111-1111-111111111111",
       *           "user_id": "11111111-1111-1111-1111-111111111111",
       *           "identity_data": {
       *             "email": "example@email.com",
       *             "email_verified": false,
       *             "phone_verified": false,
       *             "sub": "11111111-1111-1111-1111-111111111111"
       *           },
       *           "provider": "email",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "example@email.com"
       *         }
       *       ],
       *       "created_at": "2024-01-01T00:00:00Z",
       *       "updated_at": "2024-01-01T00:00:00Z",
       *       "is_anonymous": false
       *     }
       *   },
       *   "error": null
       * }
       * ```
       *
       * @example Get the logged in user with a custom access token jwt
       * ```js
       * const { data: { user } } = await supabase.auth.getUser(jwt)
       * ```
       */
      async getUser(jwt) {
        if (jwt) {
          return await this._getUser(jwt);
        }
        await this.initializePromise;
        const result = await this._acquireLock(this.lockAcquireTimeout, async () => {
          return await this._getUser();
        });
        if (result.data.user) {
          this.suppressGetSessionWarning = true;
        }
        return result;
      }
      async _getUser(jwt) {
        try {
          if (jwt) {
            return await (0, fetch_1._request)(this.fetch, "GET", `${this.url}/user`, {
              headers: this.headers,
              jwt,
              xform: fetch_1._userResponse
            });
          }
          return await this._useSession(async (result) => {
            var _a, _b, _c;
            const { data, error } = result;
            if (error) {
              throw error;
            }
            if (!((_a = data.session) === null || _a === void 0 ? void 0 : _a.access_token) && !this.hasCustomAuthorizationHeader) {
              return { data: { user: null }, error: new errors_1.AuthSessionMissingError() };
            }
            return await (0, fetch_1._request)(this.fetch, "GET", `${this.url}/user`, {
              headers: this.headers,
              jwt: (_c = (_b = data.session) === null || _b === void 0 ? void 0 : _b.access_token) !== null && _c !== void 0 ? _c : void 0,
              xform: fetch_1._userResponse
            });
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            if ((0, errors_1.isAuthSessionMissingError)(error)) {
              await this._removeSession();
              await (0, helpers_1.removeItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
            }
            return this._returnResult({ data: { user: null }, error });
          }
          throw error;
        }
      }
      /**
       * Updates user data for a logged in user.
       *
       * @category Auth
       *
       * @remarks
       * - In order to use the `updateUser()` method, the user needs to be signed in first.
       * - By default, email updates sends a confirmation link to both the user's current and new email.
       * To only send a confirmation link to the user's new email, disable **Secure email change** in your project's [email auth provider settings](/dashboard/project/_/auth/providers).
       *
       * @exampleDescription Update the email for an authenticated user
       * Sends a "Confirm Email Change" email to the new address. If **Secure Email Change** is enabled (default), confirmation is also required from the **old email** before the change is applied. To skip dual confirmation and apply the change after only the new email is verified, disable **Secure Email Change** in the [Email Auth Provider settings](/dashboard/project/_/auth/providers?provider=Email).
       *
       * @example Update the email for an authenticated user
       * ```js
       * const { data, error } = await supabase.auth.updateUser({
       *   email: 'new@email.com'
       * })
       * ```
       *
       * @exampleResponse Update the email for an authenticated user
       * ```json
       * {
       *   "data": {
       *     "user": {
       *       "id": "11111111-1111-1111-1111-111111111111",
       *       "aud": "authenticated",
       *       "role": "authenticated",
       *       "email": "example@email.com",
       *       "email_confirmed_at": "2024-01-01T00:00:00Z",
       *       "phone": "",
       *       "confirmed_at": "2024-01-01T00:00:00Z",
       *       "new_email": "new@email.com",
       *       "email_change_sent_at": "2024-01-01T00:00:00Z",
       *       "last_sign_in_at": "2024-01-01T00:00:00Z",
       *       "app_metadata": {
       *         "provider": "email",
       *         "providers": [
       *           "email"
       *         ]
       *       },
       *       "user_metadata": {
       *         "email": "example@email.com",
       *         "email_verified": false,
       *         "phone_verified": false,
       *         "sub": "11111111-1111-1111-1111-111111111111"
       *       },
       *       "identities": [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "id": "11111111-1111-1111-1111-111111111111",
       *           "user_id": "11111111-1111-1111-1111-111111111111",
       *           "identity_data": {
       *             "email": "example@email.com",
       *             "email_verified": false,
       *             "phone_verified": false,
       *             "sub": "11111111-1111-1111-1111-111111111111"
       *           },
       *           "provider": "email",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "example@email.com"
       *         }
       *       ],
       *       "created_at": "2024-01-01T00:00:00Z",
       *       "updated_at": "2024-01-01T00:00:00Z",
       *       "is_anonymous": false
       *     }
       *   },
       *   "error": null
       * }
       * ```
       *
       * @exampleDescription Update the phone number for an authenticated user
       * Sends a one-time password (OTP) to the new phone number.
       *
       * @example Update the phone number for an authenticated user
       * ```js
       * const { data, error } = await supabase.auth.updateUser({
       *   phone: '123456789'
       * })
       * ```
       *
       * @example Update the password for an authenticated user
       * ```js
       * const { data, error } = await supabase.auth.updateUser({
       *   password: 'new password'
       * })
       * ```
       *
       * @exampleDescription Update the user's metadata
       * Updates the user's custom metadata.
       *
       * **Note**: The `data` field maps to the `auth.users.raw_user_meta_data` column in your Supabase database. When calling `getUser()`, the data will be available as `user.user_metadata`.
       *
       * @example Update the user's metadata
       * ```js
       * const { data, error } = await supabase.auth.updateUser({
       *   data: { hello: 'world' }
       * })
       * ```
       *
       * @exampleDescription Update the user's password with a nonce
       * If **Secure password change** is enabled in your [project's email provider settings](/dashboard/project/_/auth/providers), updating the user's password would require a nonce if the user **hasn't recently signed in**. The nonce is sent to the user's email or phone number. A user is deemed recently signed in if the session was created in the last 24 hours.
       *
       * @example Update the user's password with a nonce
       * ```js
       * const { data, error } = await supabase.auth.updateUser({
       *   password: 'new password',
       *   nonce: '123456'
       * })
       * ```
       */
      async updateUser(attributes, options = {}) {
        await this.initializePromise;
        return await this._acquireLock(this.lockAcquireTimeout, async () => {
          return await this._updateUser(attributes, options);
        });
      }
      async _updateUser(attributes, options = {}) {
        try {
          return await this._useSession(async (result) => {
            const { data: sessionData, error: sessionError } = result;
            if (sessionError) {
              throw sessionError;
            }
            if (!sessionData.session) {
              throw new errors_1.AuthSessionMissingError();
            }
            const session = sessionData.session;
            let codeChallenge = null;
            let codeChallengeMethod = null;
            if (this.flowType === "pkce" && attributes.email != null) {
              ;
              [codeChallenge, codeChallengeMethod] = await (0, helpers_1.getCodeChallengeAndMethod)(this.storage, this.storageKey);
            }
            const { data, error: userError } = await (0, fetch_1._request)(this.fetch, "PUT", `${this.url}/user`, {
              headers: this.headers,
              redirectTo: options === null || options === void 0 ? void 0 : options.emailRedirectTo,
              body: Object.assign(Object.assign({}, attributes), { code_challenge: codeChallenge, code_challenge_method: codeChallengeMethod }),
              jwt: session.access_token,
              xform: fetch_1._userResponse
            });
            if (userError) {
              throw userError;
            }
            session.user = data.user;
            await this._saveSession(session);
            await this._notifyAllSubscribers("USER_UPDATED", session);
            return this._returnResult({ data: { user: session.user }, error: null });
          });
        } catch (error) {
          await (0, helpers_1.removeItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { user: null }, error });
          }
          throw error;
        }
      }
      /**
       * Sets the session data from the current session. If the current session is expired, setSession will take care of refreshing it to obtain a new session.
       * If the refresh token or access token in the current session is invalid, an error will be thrown.
       * @param currentSession The current session that minimally contains an access token and refresh token.
       *
       * @category Auth
       *
       * @remarks
       * - This method sets the session using an `access_token` and `refresh_token`.
       * - If successful, a `SIGNED_IN` event is emitted.
       *
       * @exampleDescription Set the session
       * Sets the session data from an access_token and refresh_token, then returns an auth response or error.
       *
       * @example Set the session
       * ```js
       *   const { data, error } = await supabase.auth.setSession({
       *     access_token,
       *     refresh_token
       *   })
       * ```
       *
       * @exampleResponse Set the session
       * ```json
       * {
       *   "data": {
       *     "user": {
       *       "id": "11111111-1111-1111-1111-111111111111",
       *       "aud": "authenticated",
       *       "role": "authenticated",
       *       "email": "example@email.com",
       *       "email_confirmed_at": "2024-01-01T00:00:00Z",
       *       "phone": "",
       *       "confirmed_at": "2024-01-01T00:00:00Z",
       *       "last_sign_in_at": "2024-01-01T00:00:00Z",
       *       "app_metadata": {
       *         "provider": "email",
       *         "providers": [
       *           "email"
       *         ]
       *       },
       *       "user_metadata": {
       *         "email": "example@email.com",
       *         "email_verified": false,
       *         "phone_verified": false,
       *         "sub": "11111111-1111-1111-1111-111111111111"
       *       },
       *       "identities": [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "id": "11111111-1111-1111-1111-111111111111",
       *           "user_id": "11111111-1111-1111-1111-111111111111",
       *           "identity_data": {
       *             "email": "example@email.com",
       *             "email_verified": false,
       *             "phone_verified": false,
       *             "sub": "11111111-1111-1111-1111-111111111111"
       *           },
       *           "provider": "email",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "example@email.com"
       *         }
       *       ],
       *       "created_at": "2024-01-01T00:00:00Z",
       *       "updated_at": "2024-01-01T00:00:00Z",
       *       "is_anonymous": false
       *     },
       *     "session": {
       *       "access_token": "<ACCESS_TOKEN>",
       *       "refresh_token": "<REFRESH_TOKEN>",
       *       "user": {
       *         "id": "11111111-1111-1111-1111-111111111111",
       *         "aud": "authenticated",
       *         "role": "authenticated",
       *         "email": "example@email.com",
       *         "email_confirmed_at": "2024-01-01T00:00:00Z",
       *         "phone": "",
       *         "confirmed_at": "2024-01-01T00:00:00Z",
       *         "last_sign_in_at": "11111111-1111-1111-1111-111111111111",
       *         "app_metadata": {
       *           "provider": "email",
       *           "providers": [
       *             "email"
       *           ]
       *         },
       *         "user_metadata": {
       *           "email": "example@email.com",
       *           "email_verified": false,
       *           "phone_verified": false,
       *           "sub": "11111111-1111-1111-1111-111111111111"
       *         },
       *         "identities": [
       *           {
       *             "identity_id": "2024-01-01T00:00:00Z",
       *             "id": "11111111-1111-1111-1111-111111111111",
       *             "user_id": "11111111-1111-1111-1111-111111111111",
       *             "identity_data": {
       *               "email": "example@email.com",
       *               "email_verified": false,
       *               "phone_verified": false,
       *               "sub": "11111111-1111-1111-1111-111111111111"
       *             },
       *             "provider": "email",
       *             "last_sign_in_at": "2024-01-01T00:00:00Z",
       *             "created_at": "2024-01-01T00:00:00Z",
       *             "updated_at": "2024-01-01T00:00:00Z",
       *             "email": "example@email.com"
       *           }
       *         ],
       *         "created_at": "2024-01-01T00:00:00Z",
       *         "updated_at": "2024-01-01T00:00:00Z",
       *         "is_anonymous": false
       *       },
       *       "token_type": "bearer",
       *       "expires_in": 3500,
       *       "expires_at": 1700000000
       *     }
       *   },
       *   "error": null
       * }
       * ```
       */
      async setSession(currentSession) {
        await this.initializePromise;
        return await this._acquireLock(this.lockAcquireTimeout, async () => {
          return await this._setSession(currentSession);
        });
      }
      async _setSession(currentSession) {
        try {
          if (!currentSession.access_token || !currentSession.refresh_token) {
            throw new errors_1.AuthSessionMissingError();
          }
          const timeNow = Date.now() / 1e3;
          let expiresAt = timeNow;
          let hasExpired = true;
          let session = null;
          const { payload } = (0, helpers_1.decodeJWT)(currentSession.access_token);
          if (payload.exp) {
            expiresAt = payload.exp;
            hasExpired = expiresAt <= timeNow;
          }
          if (hasExpired) {
            const { data: refreshedSession, error } = await this._callRefreshToken(currentSession.refresh_token);
            if (error) {
              return this._returnResult({ data: { user: null, session: null }, error });
            }
            if (!refreshedSession) {
              return { data: { user: null, session: null }, error: null };
            }
            session = refreshedSession;
          } else {
            const { data, error } = await this._getUser(currentSession.access_token);
            if (error) {
              return this._returnResult({ data: { user: null, session: null }, error });
            }
            session = {
              access_token: currentSession.access_token,
              refresh_token: currentSession.refresh_token,
              user: data.user,
              token_type: "bearer",
              expires_in: expiresAt - timeNow,
              expires_at: expiresAt
            };
            await this._saveSession(session);
            await this._notifyAllSubscribers("SIGNED_IN", session);
          }
          return this._returnResult({ data: { user: session.user, session }, error: null });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { session: null, user: null }, error });
          }
          throw error;
        }
      }
      /**
       * Returns a new session, regardless of expiry status.
       * Takes in an optional current session. If not passed in, then refreshSession() will attempt to retrieve it from getSession().
       * If the current session's refresh token is invalid, an error will be thrown.
       * @param currentSession The current session. If passed in, it must contain a refresh token.
       *
       * @category Auth
       *
       * @remarks
       * - This method will refresh and return a new session whether the current one is expired or not.
       *
       * @example Refresh session using the current session
       * ```js
       * const { data, error } = await supabase.auth.refreshSession()
       * const { session, user } = data
       * ```
       *
       * @exampleResponse Refresh session using the current session
       * ```json
       * {
       *   "data": {
       *     "user": {
       *       "id": "11111111-1111-1111-1111-111111111111",
       *       "aud": "authenticated",
       *       "role": "authenticated",
       *       "email": "example@email.com",
       *       "email_confirmed_at": "2024-01-01T00:00:00Z",
       *       "phone": "",
       *       "confirmed_at": "2024-01-01T00:00:00Z",
       *       "last_sign_in_at": "2024-01-01T00:00:00Z",
       *       "app_metadata": {
       *         "provider": "email",
       *         "providers": [
       *           "email"
       *         ]
       *       },
       *       "user_metadata": {
       *         "email": "example@email.com",
       *         "email_verified": false,
       *         "phone_verified": false,
       *         "sub": "11111111-1111-1111-1111-111111111111"
       *       },
       *       "identities": [
       *         {
       *           "identity_id": "22222222-2222-2222-2222-222222222222",
       *           "id": "11111111-1111-1111-1111-111111111111",
       *           "user_id": "11111111-1111-1111-1111-111111111111",
       *           "identity_data": {
       *             "email": "example@email.com",
       *             "email_verified": false,
       *             "phone_verified": false,
       *             "sub": "11111111-1111-1111-1111-111111111111"
       *           },
       *           "provider": "email",
       *           "last_sign_in_at": "2024-01-01T00:00:00Z",
       *           "created_at": "2024-01-01T00:00:00Z",
       *           "updated_at": "2024-01-01T00:00:00Z",
       *           "email": "example@email.com"
       *         }
       *       ],
       *       "created_at": "2024-01-01T00:00:00Z",
       *       "updated_at": "2024-01-01T00:00:00Z",
       *       "is_anonymous": false
       *     },
       *     "session": {
       *       "access_token": "<ACCESS_TOKEN>",
       *       "token_type": "bearer",
       *       "expires_in": 3600,
       *       "expires_at": 1700000000,
       *       "refresh_token": "<REFRESH_TOKEN>",
       *       "user": {
       *         "id": "11111111-1111-1111-1111-111111111111",
       *         "aud": "authenticated",
       *         "role": "authenticated",
       *         "email": "example@email.com",
       *         "email_confirmed_at": "2024-01-01T00:00:00Z",
       *         "phone": "",
       *         "confirmed_at": "2024-01-01T00:00:00Z",
       *         "last_sign_in_at": "2024-01-01T00:00:00Z",
       *         "app_metadata": {
       *           "provider": "email",
       *           "providers": [
       *             "email"
       *           ]
       *         },
       *         "user_metadata": {
       *           "email": "example@email.com",
       *           "email_verified": false,
       *           "phone_verified": false,
       *           "sub": "11111111-1111-1111-1111-111111111111"
       *         },
       *         "identities": [
       *           {
       *             "identity_id": "22222222-2222-2222-2222-222222222222",
       *             "id": "11111111-1111-1111-1111-111111111111",
       *             "user_id": "11111111-1111-1111-1111-111111111111",
       *             "identity_data": {
       *               "email": "example@email.com",
       *               "email_verified": false,
       *               "phone_verified": false,
       *               "sub": "11111111-1111-1111-1111-111111111111"
       *             },
       *             "provider": "email",
       *             "last_sign_in_at": "2024-01-01T00:00:00Z",
       *             "created_at": "2024-01-01T00:00:00Z",
       *             "updated_at": "2024-01-01T00:00:00Z",
       *             "email": "example@email.com"
       *           }
       *         ],
       *         "created_at": "2024-01-01T00:00:00Z",
       *         "updated_at": "2024-01-01T00:00:00Z",
       *         "is_anonymous": false
       *       }
       *     }
       *   },
       *   "error": null
       * }
       * ```
       *
       * @example Refresh session using a refresh token
       * ```js
       * const { data, error } = await supabase.auth.refreshSession({ refresh_token })
       * const { session, user } = data
       * ```
       */
      async refreshSession(currentSession) {
        await this.initializePromise;
        return await this._acquireLock(this.lockAcquireTimeout, async () => {
          return await this._refreshSession(currentSession);
        });
      }
      async _refreshSession(currentSession) {
        try {
          return await this._useSession(async (result) => {
            var _a;
            if (!currentSession) {
              const { data, error: error2 } = result;
              if (error2) {
                throw error2;
              }
              currentSession = (_a = data.session) !== null && _a !== void 0 ? _a : void 0;
            }
            if (!(currentSession === null || currentSession === void 0 ? void 0 : currentSession.refresh_token)) {
              throw new errors_1.AuthSessionMissingError();
            }
            const { data: session, error } = await this._callRefreshToken(currentSession.refresh_token);
            if (error) {
              return this._returnResult({ data: { user: null, session: null }, error });
            }
            if (!session) {
              return this._returnResult({ data: { user: null, session: null }, error: null });
            }
            return this._returnResult({ data: { user: session.user, session }, error: null });
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { user: null, session: null }, error });
          }
          throw error;
        }
      }
      /**
       * Gets the session data from a URL string
       */
      async _getSessionFromURL(params, callbackUrlType) {
        var _a;
        try {
          if (!(0, helpers_1.isBrowser)())
            throw new errors_1.AuthImplicitGrantRedirectError("No browser detected.");
          if (params.error || params.error_description || params.error_code) {
            throw new errors_1.AuthImplicitGrantRedirectError(params.error_description || "Error in URL with unspecified error_description", {
              error: params.error || "unspecified_error",
              code: params.error_code || "unspecified_code"
            });
          }
          switch (callbackUrlType) {
            case "implicit":
              if (this.flowType === "pkce") {
                throw new errors_1.AuthPKCEGrantCodeExchangeError("Not a valid PKCE flow url.");
              }
              break;
            case "pkce":
              if (this.flowType === "implicit") {
                throw new errors_1.AuthImplicitGrantRedirectError("Not a valid implicit grant flow url.");
              }
              break;
            default:
          }
          if (callbackUrlType === "pkce") {
            this._debug("#_initialize()", "begin", "is PKCE flow", true);
            if (!params.code)
              throw new errors_1.AuthPKCEGrantCodeExchangeError("No code detected.");
            const { data: data2, error: error2 } = await this._exchangeCodeForSession(params.code);
            if (error2)
              throw error2;
            const url = new URL(window.location.href);
            url.searchParams.delete("code");
            window.history.replaceState(window.history.state, "", url.toString());
            return {
              data: { session: data2.session, redirectType: (_a = data2.redirectType) !== null && _a !== void 0 ? _a : null },
              error: null
            };
          }
          const { provider_token, provider_refresh_token, access_token, refresh_token, expires_in, expires_at, token_type } = params;
          if (!access_token || !expires_in || !refresh_token || !token_type) {
            throw new errors_1.AuthImplicitGrantRedirectError("No session defined in URL");
          }
          const timeNow = Math.round(Date.now() / 1e3);
          const expiresIn = parseInt(expires_in);
          let expiresAt = timeNow + expiresIn;
          if (expires_at) {
            expiresAt = parseInt(expires_at);
          }
          const actuallyExpiresIn = expiresAt - timeNow;
          if (actuallyExpiresIn * 1e3 <= constants_1.AUTO_REFRESH_TICK_DURATION_MS) {
            console.warn(`@supabase/gotrue-js: Session as retrieved from URL expires in ${actuallyExpiresIn}s, should have been closer to ${expiresIn}s`);
          }
          const issuedAt = expiresAt - expiresIn;
          if (timeNow - issuedAt >= 120) {
            console.warn("@supabase/gotrue-js: Session as retrieved from URL was issued over 120s ago, URL could be stale", issuedAt, expiresAt, timeNow);
          } else if (timeNow - issuedAt < 0) {
            console.warn("@supabase/gotrue-js: Session as retrieved from URL was issued in the future? Check the device clock for skew", issuedAt, expiresAt, timeNow);
          }
          const { data, error } = await this._getUser(access_token);
          if (error)
            throw error;
          const session = {
            provider_token,
            provider_refresh_token,
            access_token,
            expires_in: expiresIn,
            expires_at: expiresAt,
            refresh_token,
            token_type,
            user: data.user
          };
          window.location.hash = "";
          this._debug("#_getSessionFromURL()", "clearing window.location.hash");
          return this._returnResult({ data: { session, redirectType: params.type }, error: null });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { session: null, redirectType: null }, error });
          }
          throw error;
        }
      }
      /**
       * Checks if the current URL contains parameters given by an implicit oauth grant flow (https://www.rfc-editor.org/rfc/rfc6749.html#section-4.2)
       *
       * If `detectSessionInUrl` is a function, it will be called with the URL and params to determine
       * if the URL should be processed as a Supabase auth callback. This allows users to exclude
       * URLs from other OAuth providers (e.g., Facebook Login) that also return access_token in the fragment.
       */
      _isImplicitGrantCallback(params) {
        if (typeof this.detectSessionInUrl === "function") {
          return this.detectSessionInUrl(new URL(window.location.href), params);
        }
        return Boolean(params.access_token || params.error_description);
      }
      /**
       * Checks if the current URL and backing storage contain parameters given by a PKCE flow
       */
      async _isPKCECallback(params) {
        const currentStorageContent = await (0, helpers_1.getItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
        return !!(params.code && currentStorageContent);
      }
      /**
       * Inside a browser context, `signOut()` will remove the logged in user from the browser session and log them out - removing all items from localstorage and then trigger a `"SIGNED_OUT"` event.
       *
       * For server-side management, you can revoke all refresh tokens for a user by passing a user's JWT through to `auth.api.signOut(JWT: string)`.
       * There is no way to revoke a user's access token jwt until it expires. It is recommended to set a shorter expiry on the jwt for this reason.
       *
       * If using `others` scope, no `SIGNED_OUT` event is fired!
       *
       * @category Auth
       *
       * @remarks
       * - In order to use the `signOut()` method, the user needs to be signed in first.
       * - By default, `signOut()` uses the global scope, which signs out all other sessions that the user is logged into as well. Customize this behavior by passing a scope parameter.
       * - Since Supabase Auth uses JWTs for authentication, the access token JWT will be valid until it's expired. When the user signs out, Supabase revokes the refresh token and deletes the JWT from the client-side. This does not revoke the JWT and it will still be valid until it expires.
       *
       * @example Sign out (all sessions)
       * ```js
       * const { error } = await supabase.auth.signOut()
       * ```
       *
       * @example Sign out (current session)
       * ```js
       * const { error } = await supabase.auth.signOut({ scope: 'local' })
       * ```
       *
       * @example Sign out (other sessions)
       * ```js
       * const { error } = await supabase.auth.signOut({ scope: 'others' })
       * ```
       */
      async signOut(options = { scope: "global" }) {
        await this.initializePromise;
        return await this._acquireLock(this.lockAcquireTimeout, async () => {
          return await this._signOut(options);
        });
      }
      async _signOut({ scope } = { scope: "global" }) {
        return await this._useSession(async (result) => {
          var _a;
          const { data, error: sessionError } = result;
          if (sessionError && !(0, errors_1.isAuthSessionMissingError)(sessionError)) {
            return this._returnResult({ error: sessionError });
          }
          const accessToken = (_a = data.session) === null || _a === void 0 ? void 0 : _a.access_token;
          if (accessToken) {
            const { error } = await this.admin.signOut(accessToken, scope);
            if (error) {
              if (!((0, errors_1.isAuthApiError)(error) && (error.status === 404 || error.status === 401 || error.status === 403) || (0, errors_1.isAuthSessionMissingError)(error))) {
                return this._returnResult({ error });
              }
            }
          }
          if (scope !== "others") {
            await this._removeSession();
            await (0, helpers_1.removeItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
          }
          return this._returnResult({ error: null });
        });
      }
      /**  *
       * @category Auth
       *
       * @remarks
       * - Subscribes to important events occurring on the user's session.
       * - Use on the frontend/client. It is less useful on the server.
       * - Events are emitted across tabs to keep your application's UI up-to-date. Some events can fire very frequently, based on the number of tabs open. Use a quick and efficient callback function, and defer or debounce as many operations as you can to be performed outside of the callback.
       * - **Important:** A callback can be an `async` function and it runs synchronously during the processing of the changes causing the event. You can easily create a dead-lock by using `await` on a call to another method of the Supabase library.
       *   - Avoid using `async` functions as callbacks.
       *   - Limit the number of `await` calls in `async` callbacks.
       *   - Do not use other Supabase functions in the callback function. If you must, dispatch the functions once the callback has finished executing. Use this as a quick way to achieve this:
       *     ```js
       *     supabase.auth.onAuthStateChange((event, session) => {
       *       setTimeout(async () => {
       *         // await on other Supabase function here
       *         // this runs right after the callback has finished
       *       }, 0)
       *     })
       *     ```
       * - Emitted events:
       *   - `INITIAL_SESSION`
       *     - Emitted right after the Supabase client is constructed and the initial session from storage is loaded.
       *   - `SIGNED_IN`
       *     - Emitted each time a user session is confirmed or re-established, including on user sign in and when refocusing a tab.
       *     - Avoid making assumptions as to when this event is fired, this may occur even when the user is already signed in. Instead, check the user object attached to the event to see if a new user has signed in and update your application's UI.
       *     - This event can fire very frequently depending on the number of tabs open in your application.
       *   - `SIGNED_OUT`
       *     - Emitted when the user signs out. This can be after:
       *       - A call to `supabase.auth.signOut()`.
       *       - After the user's session has expired for any reason:
       *         - User has signed out on another device.
       *         - The session has reached its timebox limit or inactivity timeout.
       *         - User has signed in on another device with single session per user enabled.
       *         - Check the [User Sessions](/docs/guides/auth/sessions) docs for more information.
       *     - Use this to clean up any local storage your application has associated with the user.
       *   - `TOKEN_REFRESHED`
       *     - Emitted each time a new access and refresh token are fetched for the signed in user.
       *     - It's best practice and highly recommended to extract the access token (JWT) and store it in memory for further use in your application.
       *       - Avoid frequent calls to `supabase.auth.getSession()` for the same purpose.
       *     - There is a background process that keeps track of when the session should be refreshed so you will always receive valid tokens by listening to this event.
       *     - The frequency of this event is related to the JWT expiry limit configured on your project.
       *   - `USER_UPDATED`
       *     - Emitted each time the `supabase.auth.updateUser()` method finishes successfully. Listen to it to update your application's UI based on new profile information.
       *   - `PASSWORD_RECOVERY`
       *     - Emitted instead of the `SIGNED_IN` event when the user lands on a page that includes a password recovery link in the URL.
       *     - Use it to show a UI to the user where they can [reset their password](/docs/guides/auth/passwords#resetting-a-users-password-forgot-password).
       *
       * @example Listen to auth changes
       * ```js
       * const { data } = supabase.auth.onAuthStateChange((event, session) => {
       *   console.log(event, session)
       *
       *   if (event === 'INITIAL_SESSION') {
       *     // handle initial session
       *   } else if (event === 'SIGNED_IN') {
       *     // handle sign in event
       *   } else if (event === 'SIGNED_OUT') {
       *     // handle sign out event
       *   } else if (event === 'PASSWORD_RECOVERY') {
       *     // handle password recovery event
       *   } else if (event === 'TOKEN_REFRESHED') {
       *     // handle token refreshed event
       *   } else if (event === 'USER_UPDATED') {
       *     // handle user updated event
       *   }
       * })
       *
       * // call unsubscribe to remove the callback
       * data.subscription.unsubscribe()
       * ```
       *
       * @exampleDescription Listen to sign out
       * Make sure you clear out any local data, such as local and session storage, after the client library has detected the user's sign out.
       *
       * @example Listen to sign out
       * ```js
       * supabase.auth.onAuthStateChange((event, session) => {
       *   if (event === 'SIGNED_OUT') {
       *     console.log('SIGNED_OUT', session)
       *
       *     // clear local and session storage
       *     [
       *       window.localStorage,
       *       window.sessionStorage,
       *     ].forEach((storage) => {
       *       Object.entries(storage)
       *         .forEach(([key]) => {
       *           storage.removeItem(key)
       *         })
       *     })
       *   }
       * })
       * ```
       *
       * @exampleDescription Store OAuth provider tokens on sign in
       * When using [OAuth (Social Login)](/docs/guides/auth/social-login) you sometimes wish to get access to the provider's access token and refresh token, in order to call provider APIs in the name of the user.
       *
       * For example, if you are using [Sign in with Google](/docs/guides/auth/social-login/auth-google) you may want to use the provider token to call Google APIs on behalf of the user. Supabase Auth does not keep track of the provider access and refresh token, but does return them for you once, immediately after sign in. You can use the `onAuthStateChange` method to listen for the presence of the provider tokens and store them in local storage. You can further send them to your server's APIs for use on the backend.
       *
       * Finally, make sure you remove them from local storage on the `SIGNED_OUT` event. If the OAuth provider supports token revocation, make sure you call those APIs either from the frontend or schedule them to be called on the backend.
       *
       * @example Store OAuth provider tokens on sign in
       * ```js
       * // Register this immediately after calling createClient!
       * // Because signInWithOAuth causes a redirect, you need to fetch the
       * // provider tokens from the callback.
       * supabase.auth.onAuthStateChange((event, session) => {
       *   if (session && session.provider_token) {
       *     window.localStorage.setItem('oauth_provider_token', session.provider_token)
       *   }
       *
       *   if (session && session.provider_refresh_token) {
       *     window.localStorage.setItem('oauth_provider_refresh_token', session.provider_refresh_token)
       *   }
       *
       *   if (event === 'SIGNED_OUT') {
       *     window.localStorage.removeItem('oauth_provider_token')
       *     window.localStorage.removeItem('oauth_provider_refresh_token')
       *   }
       * })
       * ```
       *
       * @exampleDescription Use React Context for the User's session
       * Instead of relying on `supabase.auth.getSession()` within your React components, you can use a [React Context](https://react.dev/reference/react/createContext) to store the latest session information from the `onAuthStateChange` callback and access it that way.
       *
       * @example Use React Context for the User's session
       * ```js
       * const SessionContext = React.createContext(null)
       *
       * function main() {
       *   const [session, setSession] = React.useState(null)
       *
       *   React.useEffect(() => {
       *     const {data: { subscription }} = supabase.auth.onAuthStateChange(
       *       (event, session) => {
       *         if (event === 'SIGNED_OUT') {
       *           setSession(null)
       *         } else if (session) {
       *           setSession(session)
       *         }
       *       })
       *
       *     return () => {
       *       subscription.unsubscribe()
       *     }
       *   }, [])
       *
       *   return (
       *     <SessionContext.Provider value={session}>
       *       <App />
       *     </SessionContext.Provider>
       *   )
       * }
       * ```
       *
       * @example Listen to password recovery events
       * ```js
       * supabase.auth.onAuthStateChange((event, session) => {
       *   if (event === 'PASSWORD_RECOVERY') {
       *     console.log('PASSWORD_RECOVERY', session)
       *     // show screen to update user's password
       *     showPasswordResetScreen(true)
       *   }
       * })
       * ```
       *
       * @example Listen to sign in
       * ```js
       * supabase.auth.onAuthStateChange((event, session) => {
       *   if (event === 'SIGNED_IN') console.log('SIGNED_IN', session)
       * })
       * ```
       *
       * @example Listen to token refresh
       * ```js
       * supabase.auth.onAuthStateChange((event, session) => {
       *   if (event === 'TOKEN_REFRESHED') console.log('TOKEN_REFRESHED', session)
       * })
       * ```
       *
       * @example Listen to user updates
       * ```js
       * supabase.auth.onAuthStateChange((event, session) => {
       *   if (event === 'USER_UPDATED') console.log('USER_UPDATED', session)
       * })
       * ```
       */
      onAuthStateChange(callback) {
        const id = (0, helpers_1.generateCallbackId)();
        const subscription = {
          id,
          callback,
          unsubscribe: () => {
            this._debug("#unsubscribe()", "state change callback with id removed", id);
            this.stateChangeEmitters.delete(id);
          }
        };
        this._debug("#onAuthStateChange()", "registered callback with id", id);
        this.stateChangeEmitters.set(id, subscription);
        (async () => {
          await this.initializePromise;
          await this._acquireLock(this.lockAcquireTimeout, async () => {
            this._emitInitialSession(id);
          });
        })();
        return { data: { subscription } };
      }
      async _emitInitialSession(id) {
        return await this._useSession(async (result) => {
          var _a, _b;
          try {
            const { data: { session }, error } = result;
            if (error)
              throw error;
            await ((_a = this.stateChangeEmitters.get(id)) === null || _a === void 0 ? void 0 : _a.callback("INITIAL_SESSION", session));
            this._debug("INITIAL_SESSION", "callback id", id, "session", session);
          } catch (err) {
            await ((_b = this.stateChangeEmitters.get(id)) === null || _b === void 0 ? void 0 : _b.callback("INITIAL_SESSION", null));
            this._debug("INITIAL_SESSION", "callback id", id, "error", err);
            if ((0, errors_1.isAuthSessionMissingError)(err)) {
              console.warn(err);
            } else {
              console.error(err);
            }
          }
        });
      }
      /**
       * Sends a password reset request to an email address. This method supports the PKCE flow.
       *
       * @param email The email address of the user.
       * @param options.redirectTo The URL to send the user to after they click the password reset link.
       * @param options.captchaToken Verification token received when the user completes the captcha on the site.
       *
       * @category Auth
       *
       * @remarks
       * - The password reset flow consist of 2 broad steps: (i) Allow the user to login via the password reset link; (ii) Update the user's password.
       * - The `resetPasswordForEmail()` only sends a password reset link to the user's email.
       * To update the user's password, see [`updateUser()`](/docs/reference/javascript/auth-updateuser).
       * - A `PASSWORD_RECOVERY` event will be emitted when the password recovery link is clicked.
       * You can use [`onAuthStateChange()`](/docs/reference/javascript/auth-onauthstatechange) to listen and invoke a callback function on these events.
       * - When the user clicks the reset link in the email they are redirected back to your application.
       * You can configure the URL that the user is redirected to with the `redirectTo` parameter.
       * See [redirect URLs and wildcards](/docs/guides/auth/redirect-urls#use-wildcards-in-redirect-urls) to add additional redirect URLs to your project.
       * - After the user has been redirected successfully, prompt them for a new password and call `updateUser()`:
       * ```js
       * const { data, error } = await supabase.auth.updateUser({
       *   password: new_password
       * })
       * ```
       *
       * @example Reset password
       * ```js
       * const { data, error } = await supabase.auth.resetPasswordForEmail(email, {
       *   redirectTo: 'https://example.com/update-password',
       * })
       * ```
       *
       * @exampleResponse Reset password
       * ```json
       * {
       *   data: {}
       *   error: null
       * }
       * ```
       *
       * @example Reset password (React)
       * ```js
       * /**
       *  * Step 1: Send the user an email to get a password reset token.
       *  * This email contains a link which sends the user back to your application.
       *  *\/
       * const { data, error } = await supabase.auth
       *   .resetPasswordForEmail('user@email.com')
       *
       * /**
       *  * Step 2: Once the user is redirected back to your application,
       *  * ask the user to reset their password.
       *  *\/
       *  useEffect(() => {
       *    supabase.auth.onAuthStateChange(async (event, session) => {
       *      if (event == "PASSWORD_RECOVERY") {
       *        const newPassword = prompt("What would you like your new password to be?");
       *        const { data, error } = await supabase.auth
       *          .updateUser({ password: newPassword })
       *
       *        if (data) alert("Password updated successfully!")
       *        if (error) alert("There was an error updating your password.")
       *      }
       *    })
       *  }, [])
       * ```
       */
      async resetPasswordForEmail(email, options = {}) {
        let codeChallenge = null;
        let codeChallengeMethod = null;
        if (this.flowType === "pkce") {
          ;
          [codeChallenge, codeChallengeMethod] = await (0, helpers_1.getCodeChallengeAndMethod)(
            this.storage,
            this.storageKey,
            true
            // isPasswordRecovery
          );
        }
        try {
          return await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/recover`, {
            body: {
              email,
              code_challenge: codeChallenge,
              code_challenge_method: codeChallengeMethod,
              gotrue_meta_security: { captcha_token: options.captchaToken }
            },
            headers: this.headers,
            redirectTo: options.redirectTo
          });
        } catch (error) {
          await (0, helpers_1.removeItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: null, error });
          }
          throw error;
        }
      }
      /**
       * Gets all the identities linked to a user.
       *
       * @category Auth
       *
       * @remarks
       * - The user needs to be signed in to call `getUserIdentities()`.
       *
       * @example Returns a list of identities linked to the user
       * ```js
       * const { data, error } = await supabase.auth.getUserIdentities()
       * ```
       *
       * @exampleResponse Returns a list of identities linked to the user
       * ```json
       * {
       *   "data": {
       *     "identities": [
       *       {
       *         "identity_id": "22222222-2222-2222-2222-222222222222",
       *         "id": "2024-01-01T00:00:00Z",
       *         "user_id": "2024-01-01T00:00:00Z",
       *         "identity_data": {
       *           "email": "example@email.com",
       *           "email_verified": false,
       *           "phone_verified": false,
       *           "sub": "11111111-1111-1111-1111-111111111111"
       *         },
       *         "provider": "email",
       *         "last_sign_in_at": "2024-01-01T00:00:00Z",
       *         "created_at": "2024-01-01T00:00:00Z",
       *         "updated_at": "2024-01-01T00:00:00Z",
       *         "email": "example@email.com"
       *       }
       *     ]
       *   },
       *   "error": null
       * }
       * ```
       */
      async getUserIdentities() {
        var _a;
        try {
          const { data, error } = await this.getUser();
          if (error)
            throw error;
          return this._returnResult({ data: { identities: (_a = data.user.identities) !== null && _a !== void 0 ? _a : [] }, error: null });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: null, error });
          }
          throw error;
        }
      }
      /**  *
       * @category Auth
       *
       * @remarks
       * - The **Enable Manual Linking** option must be enabled from your [project's authentication settings](/dashboard/project/_/auth/providers).
       * - The user needs to be signed in to call `linkIdentity()`.
       * - If the candidate identity is already linked to the existing user or another user, `linkIdentity()` will fail.
       * - If `linkIdentity` is run in the browser, the user is automatically redirected to the returned URL. On the server, you should handle the redirect.
       *
       * @example Link an identity to a user
       * ```js
       * const { data, error } = await supabase.auth.linkIdentity({
       *   provider: 'github'
       * })
       * ```
       *
       * @exampleResponse Link an identity to a user
       * ```json
       * {
       *   data: {
       *     provider: 'github',
       *     url: <PROVIDER_URL_TO_REDIRECT_TO>
       *   },
       *   error: null
       * }
       * ```
       */
      async linkIdentity(credentials) {
        if ("token" in credentials) {
          return this.linkIdentityIdToken(credentials);
        }
        return this.linkIdentityOAuth(credentials);
      }
      async linkIdentityOAuth(credentials) {
        var _a;
        try {
          const { data, error } = await this._useSession(async (result) => {
            var _a2, _b, _c, _d, _e;
            const { data: data2, error: error2 } = result;
            if (error2)
              throw error2;
            const url = await this._getUrlForProvider(`${this.url}/user/identities/authorize`, credentials.provider, {
              redirectTo: (_a2 = credentials.options) === null || _a2 === void 0 ? void 0 : _a2.redirectTo,
              scopes: (_b = credentials.options) === null || _b === void 0 ? void 0 : _b.scopes,
              queryParams: (_c = credentials.options) === null || _c === void 0 ? void 0 : _c.queryParams,
              skipBrowserRedirect: true
            });
            return await (0, fetch_1._request)(this.fetch, "GET", url, {
              headers: this.headers,
              jwt: (_e = (_d = data2.session) === null || _d === void 0 ? void 0 : _d.access_token) !== null && _e !== void 0 ? _e : void 0
            });
          });
          if (error)
            throw error;
          if ((0, helpers_1.isBrowser)() && !((_a = credentials.options) === null || _a === void 0 ? void 0 : _a.skipBrowserRedirect)) {
            window.location.assign(data === null || data === void 0 ? void 0 : data.url);
          }
          return this._returnResult({
            data: { provider: credentials.provider, url: data === null || data === void 0 ? void 0 : data.url },
            error: null
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { provider: credentials.provider, url: null }, error });
          }
          throw error;
        }
      }
      async linkIdentityIdToken(credentials) {
        return await this._useSession(async (result) => {
          var _a;
          try {
            const { error: sessionError, data: { session } } = result;
            if (sessionError)
              throw sessionError;
            const { options, provider, token, access_token, nonce } = credentials;
            const res = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/token?grant_type=id_token`, {
              headers: this.headers,
              jwt: (_a = session === null || session === void 0 ? void 0 : session.access_token) !== null && _a !== void 0 ? _a : void 0,
              body: {
                provider,
                id_token: token,
                access_token,
                nonce,
                link_identity: true,
                gotrue_meta_security: { captcha_token: options === null || options === void 0 ? void 0 : options.captchaToken }
              },
              xform: fetch_1._sessionResponse
            });
            const { data, error } = res;
            if (error) {
              return this._returnResult({ data: { user: null, session: null }, error });
            } else if (!data || !data.session || !data.user) {
              return this._returnResult({
                data: { user: null, session: null },
                error: new errors_1.AuthInvalidTokenResponseError()
              });
            }
            if (data.session) {
              await this._saveSession(data.session);
              await this._notifyAllSubscribers("USER_UPDATED", data.session);
            }
            return this._returnResult({ data, error });
          } catch (error) {
            await (0, helpers_1.removeItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
            if ((0, errors_1.isAuthError)(error)) {
              return this._returnResult({ data: { user: null, session: null }, error });
            }
            throw error;
          }
        });
      }
      /**
       * Unlinks an identity from a user by deleting it. The user will no longer be able to sign in with that identity once it's unlinked.
       *
       * @category Auth
       *
       * @remarks
       * - The **Enable Manual Linking** option must be enabled from your [project's authentication settings](/dashboard/project/_/auth/providers).
       * - The user needs to be signed in to call `unlinkIdentity()`.
       * - The user must have at least 2 identities in order to unlink an identity.
       * - The identity to be unlinked must belong to the user.
       *
       * @example Unlink an identity
       * ```js
       * // retrieve all identities linked to a user
       * const identities = await supabase.auth.getUserIdentities()
       *
       * // find the google identity
       * const googleIdentity = identities.find(
       *   identity => identity.provider === 'google'
       * )
       *
       * // unlink the google identity
       * const { error } = await supabase.auth.unlinkIdentity(googleIdentity)
       * ```
       */
      async unlinkIdentity(identity) {
        try {
          return await this._useSession(async (result) => {
            var _a, _b;
            const { data, error } = result;
            if (error) {
              throw error;
            }
            return await (0, fetch_1._request)(this.fetch, "DELETE", `${this.url}/user/identities/${identity.identity_id}`, {
              headers: this.headers,
              jwt: (_b = (_a = data.session) === null || _a === void 0 ? void 0 : _a.access_token) !== null && _b !== void 0 ? _b : void 0
            });
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: null, error });
          }
          throw error;
        }
      }
      /**
       * Generates a new JWT.
       * @param refreshToken A valid refresh token that was returned on login.
       */
      async _refreshAccessToken(refreshToken) {
        const debugName = `#_refreshAccessToken(${refreshToken.substring(0, 5)}...)`;
        this._debug(debugName, "begin");
        try {
          const startedAt = Date.now();
          return await (0, helpers_1.retryable)(async (attempt) => {
            if (attempt > 0) {
              await (0, helpers_1.sleep)(200 * Math.pow(2, attempt - 1));
            }
            this._debug(debugName, "refreshing attempt", attempt);
            return await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/token?grant_type=refresh_token`, {
              body: { refresh_token: refreshToken },
              headers: this.headers,
              xform: fetch_1._sessionResponse
            });
          }, (attempt, error) => {
            const nextBackOffInterval = 200 * Math.pow(2, attempt);
            return error && (0, errors_1.isAuthRetryableFetchError)(error) && // retryable only if the request can be sent before the backoff overflows the tick duration
            Date.now() + nextBackOffInterval - startedAt < constants_1.AUTO_REFRESH_TICK_DURATION_MS;
          });
        } catch (error) {
          this._debug(debugName, "error", error);
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: { session: null, user: null }, error });
          }
          throw error;
        } finally {
          this._debug(debugName, "end");
        }
      }
      _isValidSession(maybeSession) {
        const isValidSession = typeof maybeSession === "object" && maybeSession !== null && "access_token" in maybeSession && "refresh_token" in maybeSession && "expires_at" in maybeSession;
        return isValidSession;
      }
      async _handleProviderSignIn(provider, options) {
        const url = await this._getUrlForProvider(`${this.url}/authorize`, provider, {
          redirectTo: options.redirectTo,
          scopes: options.scopes,
          queryParams: options.queryParams
        });
        this._debug("#_handleProviderSignIn()", "provider", provider, "options", options, "url", url);
        if ((0, helpers_1.isBrowser)() && !options.skipBrowserRedirect) {
          window.location.assign(url);
        }
        return { data: { provider, url }, error: null };
      }
      /**
       * Recovers the session from LocalStorage and refreshes the token
       * Note: this method is async to accommodate for AsyncStorage e.g. in React native.
       */
      async _recoverAndRefresh() {
        var _a, _b;
        const debugName = "#_recoverAndRefresh()";
        this._debug(debugName, "begin");
        try {
          const currentSession = await (0, helpers_1.getItemAsync)(this.storage, this.storageKey);
          if (currentSession && this.userStorage) {
            let maybeUser = await (0, helpers_1.getItemAsync)(this.userStorage, this.storageKey + "-user");
            if (!this.storage.isServer && Object.is(this.storage, this.userStorage) && !maybeUser) {
              maybeUser = { user: currentSession.user };
              await (0, helpers_1.setItemAsync)(this.userStorage, this.storageKey + "-user", maybeUser);
            }
            currentSession.user = (_a = maybeUser === null || maybeUser === void 0 ? void 0 : maybeUser.user) !== null && _a !== void 0 ? _a : (0, helpers_1.userNotAvailableProxy)();
          } else if (currentSession && !currentSession.user) {
            if (!currentSession.user) {
              const separateUser = await (0, helpers_1.getItemAsync)(this.storage, this.storageKey + "-user");
              if (separateUser && (separateUser === null || separateUser === void 0 ? void 0 : separateUser.user)) {
                currentSession.user = separateUser.user;
                await (0, helpers_1.removeItemAsync)(this.storage, this.storageKey + "-user");
                await (0, helpers_1.setItemAsync)(this.storage, this.storageKey, currentSession);
              } else {
                currentSession.user = (0, helpers_1.userNotAvailableProxy)();
              }
            }
          }
          this._debug(debugName, "session from storage", currentSession);
          if (!this._isValidSession(currentSession)) {
            this._debug(debugName, "session is not valid");
            if (currentSession !== null) {
              await this._removeSession();
            }
            return;
          }
          const expiresWithMargin = ((_b = currentSession.expires_at) !== null && _b !== void 0 ? _b : Infinity) * 1e3 - Date.now() < constants_1.EXPIRY_MARGIN_MS;
          this._debug(debugName, `session has${expiresWithMargin ? "" : " not"} expired with margin of ${constants_1.EXPIRY_MARGIN_MS}s`);
          if (expiresWithMargin) {
            if (this.autoRefreshToken && currentSession.refresh_token) {
              const { error } = await this._callRefreshToken(currentSession.refresh_token);
              if (error) {
                console.error(error);
                if (!(0, errors_1.isAuthRetryableFetchError)(error)) {
                  this._debug(debugName, "refresh failed with a non-retryable error, removing the session", error);
                  await this._removeSession();
                }
              }
            }
          } else if (currentSession.user && currentSession.user.__isUserNotAvailableProxy === true) {
            try {
              const { data, error: userError } = await this._getUser(currentSession.access_token);
              if (!userError && (data === null || data === void 0 ? void 0 : data.user)) {
                currentSession.user = data.user;
                await this._saveSession(currentSession);
                await this._notifyAllSubscribers("SIGNED_IN", currentSession);
              } else {
                this._debug(debugName, "could not get user data, skipping SIGNED_IN notification");
              }
            } catch (getUserError) {
              console.error("Error getting user data:", getUserError);
              this._debug(debugName, "error getting user data, skipping SIGNED_IN notification", getUserError);
            }
          } else {
            await this._notifyAllSubscribers("SIGNED_IN", currentSession);
          }
        } catch (err) {
          this._debug(debugName, "error", err);
          console.error(err);
          return;
        } finally {
          this._debug(debugName, "end");
        }
      }
      async _callRefreshToken(refreshToken) {
        var _a, _b;
        if (!refreshToken) {
          throw new errors_1.AuthSessionMissingError();
        }
        if (this.refreshingDeferred) {
          return this.refreshingDeferred.promise;
        }
        const debugName = `#_callRefreshToken(${refreshToken.substring(0, 5)}...)`;
        this._debug(debugName, "begin");
        try {
          this.refreshingDeferred = new helpers_1.Deferred();
          const { data, error } = await this._refreshAccessToken(refreshToken);
          if (error)
            throw error;
          if (!data.session)
            throw new errors_1.AuthSessionMissingError();
          await this._saveSession(data.session);
          await this._notifyAllSubscribers("TOKEN_REFRESHED", data.session);
          const result = { data: data.session, error: null };
          this.refreshingDeferred.resolve(result);
          return result;
        } catch (error) {
          this._debug(debugName, "error", error);
          if ((0, errors_1.isAuthError)(error)) {
            const result = { data: null, error };
            if (!(0, errors_1.isAuthRetryableFetchError)(error)) {
              await this._removeSession();
            }
            (_a = this.refreshingDeferred) === null || _a === void 0 ? void 0 : _a.resolve(result);
            return result;
          }
          (_b = this.refreshingDeferred) === null || _b === void 0 ? void 0 : _b.reject(error);
          throw error;
        } finally {
          this.refreshingDeferred = null;
          this._debug(debugName, "end");
        }
      }
      async _notifyAllSubscribers(event, session, broadcast = true) {
        const debugName = `#_notifyAllSubscribers(${event})`;
        this._debug(debugName, "begin", session, `broadcast = ${broadcast}`);
        try {
          if (this.broadcastChannel && broadcast) {
            this.broadcastChannel.postMessage({ event, session });
          }
          const errors = [];
          const promises = Array.from(this.stateChangeEmitters.values()).map(async (x) => {
            try {
              await x.callback(event, session);
            } catch (e) {
              errors.push(e);
            }
          });
          await Promise.all(promises);
          if (errors.length > 0) {
            for (let i = 0; i < errors.length; i += 1) {
              console.error(errors[i]);
            }
            throw errors[0];
          }
        } finally {
          this._debug(debugName, "end");
        }
      }
      /**
       * set currentSession and currentUser
       * process to _startAutoRefreshToken if possible
       */
      async _saveSession(session) {
        this._debug("#_saveSession()", session);
        this.suppressGetSessionWarning = true;
        await (0, helpers_1.removeItemAsync)(this.storage, `${this.storageKey}-code-verifier`);
        const sessionToProcess = Object.assign({}, session);
        const userIsProxy = sessionToProcess.user && sessionToProcess.user.__isUserNotAvailableProxy === true;
        if (this.userStorage) {
          if (!userIsProxy && sessionToProcess.user) {
            await (0, helpers_1.setItemAsync)(this.userStorage, this.storageKey + "-user", {
              user: sessionToProcess.user
            });
          } else if (userIsProxy) {
          }
          const mainSessionData = Object.assign({}, sessionToProcess);
          delete mainSessionData.user;
          const clonedMainSessionData = (0, helpers_1.deepClone)(mainSessionData);
          await (0, helpers_1.setItemAsync)(this.storage, this.storageKey, clonedMainSessionData);
        } else {
          const clonedSession = (0, helpers_1.deepClone)(sessionToProcess);
          await (0, helpers_1.setItemAsync)(this.storage, this.storageKey, clonedSession);
        }
      }
      async _removeSession() {
        this._debug("#_removeSession()");
        this.suppressGetSessionWarning = false;
        await (0, helpers_1.removeItemAsync)(this.storage, this.storageKey);
        await (0, helpers_1.removeItemAsync)(this.storage, this.storageKey + "-code-verifier");
        await (0, helpers_1.removeItemAsync)(this.storage, this.storageKey + "-user");
        if (this.userStorage) {
          await (0, helpers_1.removeItemAsync)(this.userStorage, this.storageKey + "-user");
        }
        await this._notifyAllSubscribers("SIGNED_OUT", null);
      }
      /**
       * Removes any registered visibilitychange callback.
       *
       * {@see #startAutoRefresh}
       * {@see #stopAutoRefresh}
       */
      _removeVisibilityChangedCallback() {
        this._debug("#_removeVisibilityChangedCallback()");
        const callback = this.visibilityChangedCallback;
        this.visibilityChangedCallback = null;
        try {
          if (callback && (0, helpers_1.isBrowser)() && (window === null || window === void 0 ? void 0 : window.removeEventListener)) {
            window.removeEventListener("visibilitychange", callback);
          }
        } catch (e) {
          console.error("removing visibilitychange callback failed", e);
        }
      }
      /**
       * This is the private implementation of {@link #startAutoRefresh}. Use this
       * within the library.
       */
      async _startAutoRefresh() {
        await this._stopAutoRefresh();
        this._debug("#_startAutoRefresh()");
        const ticker = setInterval(() => this._autoRefreshTokenTick(), constants_1.AUTO_REFRESH_TICK_DURATION_MS);
        this.autoRefreshTicker = ticker;
        if (ticker && typeof ticker === "object" && typeof ticker.unref === "function") {
          ticker.unref();
        } else if (typeof Deno !== "undefined" && typeof Deno.unrefTimer === "function") {
          Deno.unrefTimer(ticker);
        }
        const timeout = setTimeout(async () => {
          await this.initializePromise;
          await this._autoRefreshTokenTick();
        }, 0);
        this.autoRefreshTickTimeout = timeout;
        if (timeout && typeof timeout === "object" && typeof timeout.unref === "function") {
          timeout.unref();
        } else if (typeof Deno !== "undefined" && typeof Deno.unrefTimer === "function") {
          Deno.unrefTimer(timeout);
        }
      }
      /**
       * This is the private implementation of {@link #stopAutoRefresh}. Use this
       * within the library.
       */
      async _stopAutoRefresh() {
        this._debug("#_stopAutoRefresh()");
        const ticker = this.autoRefreshTicker;
        this.autoRefreshTicker = null;
        if (ticker) {
          clearInterval(ticker);
        }
        const timeout = this.autoRefreshTickTimeout;
        this.autoRefreshTickTimeout = null;
        if (timeout) {
          clearTimeout(timeout);
        }
      }
      /**
       * Starts an auto-refresh process in the background. The session is checked
       * every few seconds. Close to the time of expiration a process is started to
       * refresh the session. If refreshing fails it will be retried for as long as
       * necessary.
       *
       * If you set the {@link GoTrueClientOptions#autoRefreshToken} you don't need
       * to call this function, it will be called for you.
       *
       * On browsers the refresh process works only when the tab/window is in the
       * foreground to conserve resources as well as prevent race conditions and
       * flooding auth with requests. If you call this method any managed
       * visibility change callback will be removed and you must manage visibility
       * changes on your own.
       *
       * On non-browser platforms the refresh process works *continuously* in the
       * background, which may not be desirable. You should hook into your
       * platform's foreground indication mechanism and call these methods
       * appropriately to conserve resources.
       *
       * {@see #stopAutoRefresh}
       *
       * @category Auth
       *
       * @remarks
       * - Only useful in non-browser environments such as React Native or Electron.
       * - The Supabase Auth library automatically starts and stops proactively refreshing the session when a tab is focused or not.
       * - On non-browser platforms, such as mobile or desktop apps built with web technologies, the library is not able to effectively determine whether the application is _focused_ or not.
       * - To give this hint to the application, you should be calling this method when the app is in focus and calling `supabase.auth.stopAutoRefresh()` when it's out of focus.
       *
       * @example Start and stop auto refresh in React Native
       * ```js
       * import { AppState } from 'react-native'
       *
       * // make sure you register this only once!
       * AppState.addEventListener('change', (state) => {
       *   if (state === 'active') {
       *     supabase.auth.startAutoRefresh()
       *   } else {
       *     supabase.auth.stopAutoRefresh()
       *   }
       * })
       * ```
       */
      async startAutoRefresh() {
        this._removeVisibilityChangedCallback();
        await this._startAutoRefresh();
      }
      /**
       * Stops an active auto refresh process running in the background (if any).
       *
       * If you call this method any managed visibility change callback will be
       * removed and you must manage visibility changes on your own.
       *
       * See {@link #startAutoRefresh} for more details.
       *
       * @category Auth
       *
       * @remarks
       * - Only useful in non-browser environments such as React Native or Electron.
       * - The Supabase Auth library automatically starts and stops proactively refreshing the session when a tab is focused or not.
       * - On non-browser platforms, such as mobile or desktop apps built with web technologies, the library is not able to effectively determine whether the application is _focused_ or not.
       * - When your application goes in the background or out of focus, call this method to stop the proactive refreshing of the session.
       *
       * @example Start and stop auto refresh in React Native
       * ```js
       * import { AppState } from 'react-native'
       *
       * // make sure you register this only once!
       * AppState.addEventListener('change', (state) => {
       *   if (state === 'active') {
       *     supabase.auth.startAutoRefresh()
       *   } else {
       *     supabase.auth.stopAutoRefresh()
       *   }
       * })
       * ```
       */
      async stopAutoRefresh() {
        this._removeVisibilityChangedCallback();
        await this._stopAutoRefresh();
      }
      /**
       * Runs the auto refresh token tick.
       */
      async _autoRefreshTokenTick() {
        this._debug("#_autoRefreshTokenTick()", "begin");
        try {
          await this._acquireLock(0, async () => {
            try {
              const now = Date.now();
              try {
                return await this._useSession(async (result) => {
                  const { data: { session } } = result;
                  if (!session || !session.refresh_token || !session.expires_at) {
                    this._debug("#_autoRefreshTokenTick()", "no session");
                    return;
                  }
                  const expiresInTicks = Math.floor((session.expires_at * 1e3 - now) / constants_1.AUTO_REFRESH_TICK_DURATION_MS);
                  this._debug("#_autoRefreshTokenTick()", `access token expires in ${expiresInTicks} ticks, a tick lasts ${constants_1.AUTO_REFRESH_TICK_DURATION_MS}ms, refresh threshold is ${constants_1.AUTO_REFRESH_TICK_THRESHOLD} ticks`);
                  if (expiresInTicks <= constants_1.AUTO_REFRESH_TICK_THRESHOLD) {
                    await this._callRefreshToken(session.refresh_token);
                  }
                });
              } catch (e) {
                console.error("Auto refresh tick failed with error. This is likely a transient error.", e);
              }
            } finally {
              this._debug("#_autoRefreshTokenTick()", "end");
            }
          });
        } catch (e) {
          if (e.isAcquireTimeout || e instanceof locks_1.LockAcquireTimeoutError) {
            this._debug("auto refresh token tick lock not available");
          } else {
            throw e;
          }
        }
      }
      /**
       * Registers callbacks on the browser / platform, which in-turn run
       * algorithms when the browser window/tab are in foreground. On non-browser
       * platforms it assumes always foreground.
       */
      async _handleVisibilityChange() {
        this._debug("#_handleVisibilityChange()");
        if (!(0, helpers_1.isBrowser)() || !(window === null || window === void 0 ? void 0 : window.addEventListener)) {
          if (this.autoRefreshToken) {
            this.startAutoRefresh();
          }
          return false;
        }
        try {
          this.visibilityChangedCallback = async () => {
            try {
              await this._onVisibilityChanged(false);
            } catch (error) {
              this._debug("#visibilityChangedCallback", "error", error);
            }
          };
          window === null || window === void 0 ? void 0 : window.addEventListener("visibilitychange", this.visibilityChangedCallback);
          await this._onVisibilityChanged(true);
        } catch (error) {
          console.error("_handleVisibilityChange", error);
        }
      }
      /**
       * Callback registered with `window.addEventListener('visibilitychange')`.
       */
      async _onVisibilityChanged(calledFromInitialize) {
        const methodName = `#_onVisibilityChanged(${calledFromInitialize})`;
        this._debug(methodName, "visibilityState", document.visibilityState);
        if (document.visibilityState === "visible") {
          if (this.autoRefreshToken) {
            this._startAutoRefresh();
          }
          if (!calledFromInitialize) {
            await this.initializePromise;
            await this._acquireLock(this.lockAcquireTimeout, async () => {
              if (document.visibilityState !== "visible") {
                this._debug(methodName, "acquired the lock to recover the session, but the browser visibilityState is no longer visible, aborting");
                return;
              }
              await this._recoverAndRefresh();
            });
          }
        } else if (document.visibilityState === "hidden") {
          if (this.autoRefreshToken) {
            this._stopAutoRefresh();
          }
        }
      }
      /**
       * Generates the relevant login URL for a third-party provider.
       * @param options.redirectTo A URL or mobile address to send the user to after they are confirmed.
       * @param options.scopes A space-separated list of scopes granted to the OAuth application.
       * @param options.queryParams An object of key-value pairs containing query parameters granted to the OAuth application.
       */
      async _getUrlForProvider(url, provider, options) {
        const urlParams = [`provider=${encodeURIComponent(provider)}`];
        if (options === null || options === void 0 ? void 0 : options.redirectTo) {
          urlParams.push(`redirect_to=${encodeURIComponent(options.redirectTo)}`);
        }
        if (options === null || options === void 0 ? void 0 : options.scopes) {
          urlParams.push(`scopes=${encodeURIComponent(options.scopes)}`);
        }
        if (this.flowType === "pkce") {
          const [codeChallenge, codeChallengeMethod] = await (0, helpers_1.getCodeChallengeAndMethod)(this.storage, this.storageKey);
          const flowParams = new URLSearchParams({
            code_challenge: `${encodeURIComponent(codeChallenge)}`,
            code_challenge_method: `${encodeURIComponent(codeChallengeMethod)}`
          });
          urlParams.push(flowParams.toString());
        }
        if (options === null || options === void 0 ? void 0 : options.queryParams) {
          const query = new URLSearchParams(options.queryParams);
          urlParams.push(query.toString());
        }
        if (options === null || options === void 0 ? void 0 : options.skipBrowserRedirect) {
          urlParams.push(`skip_http_redirect=${options.skipBrowserRedirect}`);
        }
        return `${url}?${urlParams.join("&")}`;
      }
      async _unenroll(params) {
        try {
          return await this._useSession(async (result) => {
            var _a;
            const { data: sessionData, error: sessionError } = result;
            if (sessionError) {
              return this._returnResult({ data: null, error: sessionError });
            }
            return await (0, fetch_1._request)(this.fetch, "DELETE", `${this.url}/factors/${params.factorId}`, {
              headers: this.headers,
              jwt: (_a = sessionData === null || sessionData === void 0 ? void 0 : sessionData.session) === null || _a === void 0 ? void 0 : _a.access_token
            });
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: null, error });
          }
          throw error;
        }
      }
      async _enroll(params) {
        try {
          return await this._useSession(async (result) => {
            var _a, _b;
            const { data: sessionData, error: sessionError } = result;
            if (sessionError) {
              return this._returnResult({ data: null, error: sessionError });
            }
            const body = Object.assign({ friendly_name: params.friendlyName, factor_type: params.factorType }, params.factorType === "phone" ? { phone: params.phone } : params.factorType === "totp" ? { issuer: params.issuer } : {});
            const { data, error } = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/factors`, {
              body,
              headers: this.headers,
              jwt: (_a = sessionData === null || sessionData === void 0 ? void 0 : sessionData.session) === null || _a === void 0 ? void 0 : _a.access_token
            });
            if (error) {
              return this._returnResult({ data: null, error });
            }
            if (params.factorType === "totp" && data.type === "totp" && ((_b = data === null || data === void 0 ? void 0 : data.totp) === null || _b === void 0 ? void 0 : _b.qr_code)) {
              data.totp.qr_code = `data:image/svg+xml;utf-8,${data.totp.qr_code}`;
            }
            return this._returnResult({ data, error: null });
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: null, error });
          }
          throw error;
        }
      }
      async _verify(params) {
        return this._acquireLock(this.lockAcquireTimeout, async () => {
          try {
            return await this._useSession(async (result) => {
              var _a;
              const { data: sessionData, error: sessionError } = result;
              if (sessionError) {
                return this._returnResult({ data: null, error: sessionError });
              }
              const body = Object.assign({ challenge_id: params.challengeId }, "webauthn" in params ? {
                webauthn: Object.assign(Object.assign({}, params.webauthn), { credential_response: params.webauthn.type === "create" ? (0, webauthn_1.serializeCredentialCreationResponse)(params.webauthn.credential_response) : (0, webauthn_1.serializeCredentialRequestResponse)(params.webauthn.credential_response) })
              } : { code: params.code });
              const { data, error } = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/factors/${params.factorId}/verify`, {
                body,
                headers: this.headers,
                jwt: (_a = sessionData === null || sessionData === void 0 ? void 0 : sessionData.session) === null || _a === void 0 ? void 0 : _a.access_token
              });
              if (error) {
                return this._returnResult({ data: null, error });
              }
              await this._saveSession(Object.assign({ expires_at: Math.round(Date.now() / 1e3) + data.expires_in }, data));
              await this._notifyAllSubscribers("MFA_CHALLENGE_VERIFIED", data);
              return this._returnResult({ data, error });
            });
          } catch (error) {
            if ((0, errors_1.isAuthError)(error)) {
              return this._returnResult({ data: null, error });
            }
            throw error;
          }
        });
      }
      async _challenge(params) {
        return this._acquireLock(this.lockAcquireTimeout, async () => {
          try {
            return await this._useSession(async (result) => {
              var _a;
              const { data: sessionData, error: sessionError } = result;
              if (sessionError) {
                return this._returnResult({ data: null, error: sessionError });
              }
              const response2 = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/factors/${params.factorId}/challenge`, {
                body: params,
                headers: this.headers,
                jwt: (_a = sessionData === null || sessionData === void 0 ? void 0 : sessionData.session) === null || _a === void 0 ? void 0 : _a.access_token
              });
              if (response2.error) {
                return response2;
              }
              const { data } = response2;
              if (data.type !== "webauthn") {
                return { data, error: null };
              }
              switch (data.webauthn.type) {
                case "create":
                  return {
                    data: Object.assign(Object.assign({}, data), { webauthn: Object.assign(Object.assign({}, data.webauthn), { credential_options: Object.assign(Object.assign({}, data.webauthn.credential_options), { publicKey: (0, webauthn_1.deserializeCredentialCreationOptions)(data.webauthn.credential_options.publicKey) }) }) }),
                    error: null
                  };
                case "request":
                  return {
                    data: Object.assign(Object.assign({}, data), { webauthn: Object.assign(Object.assign({}, data.webauthn), { credential_options: Object.assign(Object.assign({}, data.webauthn.credential_options), { publicKey: (0, webauthn_1.deserializeCredentialRequestOptions)(data.webauthn.credential_options.publicKey) }) }) }),
                    error: null
                  };
              }
            });
          } catch (error) {
            if ((0, errors_1.isAuthError)(error)) {
              return this._returnResult({ data: null, error });
            }
            throw error;
          }
        });
      }
      /**
       * {@see GoTrueMFAApi#challengeAndVerify}
       */
      async _challengeAndVerify(params) {
        const { data: challengeData, error: challengeError } = await this._challenge({
          factorId: params.factorId
        });
        if (challengeError) {
          return this._returnResult({ data: null, error: challengeError });
        }
        return await this._verify({
          factorId: params.factorId,
          challengeId: challengeData.id,
          code: params.code
        });
      }
      /**
       * {@see GoTrueMFAApi#listFactors}
       */
      async _listFactors() {
        var _a;
        const { data: { user }, error: userError } = await this.getUser();
        if (userError) {
          return { data: null, error: userError };
        }
        const data = {
          all: [],
          phone: [],
          totp: [],
          webauthn: []
        };
        for (const factor of (_a = user === null || user === void 0 ? void 0 : user.factors) !== null && _a !== void 0 ? _a : []) {
          data.all.push(factor);
          if (factor.status === "verified") {
            ;
            data[factor.factor_type].push(factor);
          }
        }
        return {
          data,
          error: null
        };
      }
      /**
       * {@see GoTrueMFAApi#getAuthenticatorAssuranceLevel}
       */
      async _getAuthenticatorAssuranceLevel(jwt) {
        var _a, _b, _c, _d;
        if (jwt) {
          try {
            const { payload: payload2 } = (0, helpers_1.decodeJWT)(jwt);
            let currentLevel2 = null;
            if (payload2.aal) {
              currentLevel2 = payload2.aal;
            }
            let nextLevel2 = currentLevel2;
            const { data: { user }, error: userError } = await this.getUser(jwt);
            if (userError) {
              return this._returnResult({ data: null, error: userError });
            }
            const verifiedFactors2 = (_b = (_a = user === null || user === void 0 ? void 0 : user.factors) === null || _a === void 0 ? void 0 : _a.filter((factor) => factor.status === "verified")) !== null && _b !== void 0 ? _b : [];
            if (verifiedFactors2.length > 0) {
              nextLevel2 = "aal2";
            }
            const currentAuthenticationMethods2 = payload2.amr || [];
            return { data: { currentLevel: currentLevel2, nextLevel: nextLevel2, currentAuthenticationMethods: currentAuthenticationMethods2 }, error: null };
          } catch (error) {
            if ((0, errors_1.isAuthError)(error)) {
              return this._returnResult({ data: null, error });
            }
            throw error;
          }
        }
        const { data: { session }, error: sessionError } = await this.getSession();
        if (sessionError) {
          return this._returnResult({ data: null, error: sessionError });
        }
        if (!session) {
          return {
            data: { currentLevel: null, nextLevel: null, currentAuthenticationMethods: [] },
            error: null
          };
        }
        const { payload } = (0, helpers_1.decodeJWT)(session.access_token);
        let currentLevel = null;
        if (payload.aal) {
          currentLevel = payload.aal;
        }
        let nextLevel = currentLevel;
        const verifiedFactors = (_d = (_c = session.user.factors) === null || _c === void 0 ? void 0 : _c.filter((factor) => factor.status === "verified")) !== null && _d !== void 0 ? _d : [];
        if (verifiedFactors.length > 0) {
          nextLevel = "aal2";
        }
        const currentAuthenticationMethods = payload.amr || [];
        return { data: { currentLevel, nextLevel, currentAuthenticationMethods }, error: null };
      }
      /**
       * Retrieves details about an OAuth authorization request.
       * Only relevant when the OAuth 2.1 server is enabled in Supabase Auth.
       *
       * Returns authorization details including client info, scopes, and user information.
       * If the response includes only a redirect_url field, it means consent was already given - the caller
       * should handle the redirect manually if needed.
       */
      async _getAuthorizationDetails(authorizationId) {
        try {
          return await this._useSession(async (result) => {
            const { data: { session }, error: sessionError } = result;
            if (sessionError) {
              return this._returnResult({ data: null, error: sessionError });
            }
            if (!session) {
              return this._returnResult({ data: null, error: new errors_1.AuthSessionMissingError() });
            }
            return await (0, fetch_1._request)(this.fetch, "GET", `${this.url}/oauth/authorizations/${authorizationId}`, {
              headers: this.headers,
              jwt: session.access_token,
              xform: (data) => ({ data, error: null })
            });
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: null, error });
          }
          throw error;
        }
      }
      /**
       * Approves an OAuth authorization request.
       * Only relevant when the OAuth 2.1 server is enabled in Supabase Auth.
       */
      async _approveAuthorization(authorizationId, options) {
        try {
          return await this._useSession(async (result) => {
            const { data: { session }, error: sessionError } = result;
            if (sessionError) {
              return this._returnResult({ data: null, error: sessionError });
            }
            if (!session) {
              return this._returnResult({ data: null, error: new errors_1.AuthSessionMissingError() });
            }
            const response2 = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/oauth/authorizations/${authorizationId}/consent`, {
              headers: this.headers,
              jwt: session.access_token,
              body: { action: "approve" },
              xform: (data) => ({ data, error: null })
            });
            if (response2.data && response2.data.redirect_url) {
              if ((0, helpers_1.isBrowser)() && !(options === null || options === void 0 ? void 0 : options.skipBrowserRedirect)) {
                window.location.assign(response2.data.redirect_url);
              }
            }
            return response2;
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: null, error });
          }
          throw error;
        }
      }
      /**
       * Denies an OAuth authorization request.
       * Only relevant when the OAuth 2.1 server is enabled in Supabase Auth.
       */
      async _denyAuthorization(authorizationId, options) {
        try {
          return await this._useSession(async (result) => {
            const { data: { session }, error: sessionError } = result;
            if (sessionError) {
              return this._returnResult({ data: null, error: sessionError });
            }
            if (!session) {
              return this._returnResult({ data: null, error: new errors_1.AuthSessionMissingError() });
            }
            const response2 = await (0, fetch_1._request)(this.fetch, "POST", `${this.url}/oauth/authorizations/${authorizationId}/consent`, {
              headers: this.headers,
              jwt: session.access_token,
              body: { action: "deny" },
              xform: (data) => ({ data, error: null })
            });
            if (response2.data && response2.data.redirect_url) {
              if ((0, helpers_1.isBrowser)() && !(options === null || options === void 0 ? void 0 : options.skipBrowserRedirect)) {
                window.location.assign(response2.data.redirect_url);
              }
            }
            return response2;
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: null, error });
          }
          throw error;
        }
      }
      /**
       * Lists all OAuth grants that the authenticated user has authorized.
       * Only relevant when the OAuth 2.1 server is enabled in Supabase Auth.
       */
      async _listOAuthGrants() {
        try {
          return await this._useSession(async (result) => {
            const { data: { session }, error: sessionError } = result;
            if (sessionError) {
              return this._returnResult({ data: null, error: sessionError });
            }
            if (!session) {
              return this._returnResult({ data: null, error: new errors_1.AuthSessionMissingError() });
            }
            return await (0, fetch_1._request)(this.fetch, "GET", `${this.url}/user/oauth/grants`, {
              headers: this.headers,
              jwt: session.access_token,
              xform: (data) => ({ data, error: null })
            });
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: null, error });
          }
          throw error;
        }
      }
      /**
       * Revokes a user's OAuth grant for a specific client.
       * Only relevant when the OAuth 2.1 server is enabled in Supabase Auth.
       */
      async _revokeOAuthGrant(options) {
        try {
          return await this._useSession(async (result) => {
            const { data: { session }, error: sessionError } = result;
            if (sessionError) {
              return this._returnResult({ data: null, error: sessionError });
            }
            if (!session) {
              return this._returnResult({ data: null, error: new errors_1.AuthSessionMissingError() });
            }
            await (0, fetch_1._request)(this.fetch, "DELETE", `${this.url}/user/oauth/grants`, {
              headers: this.headers,
              jwt: session.access_token,
              query: { client_id: options.clientId },
              noResolveJson: true
            });
            return { data: {}, error: null };
          });
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: null, error });
          }
          throw error;
        }
      }
      async fetchJwk(kid, jwks = { keys: [] }) {
        let jwk = jwks.keys.find((key) => key.kid === kid);
        if (jwk) {
          return jwk;
        }
        const now = Date.now();
        jwk = this.jwks.keys.find((key) => key.kid === kid);
        if (jwk && this.jwks_cached_at + constants_1.JWKS_TTL > now) {
          return jwk;
        }
        const { data, error } = await (0, fetch_1._request)(this.fetch, "GET", `${this.url}/.well-known/jwks.json`, {
          headers: this.headers
        });
        if (error) {
          throw error;
        }
        if (!data.keys || data.keys.length === 0) {
          return null;
        }
        this.jwks = data;
        this.jwks_cached_at = now;
        jwk = data.keys.find((key) => key.kid === kid);
        if (!jwk) {
          return null;
        }
        return jwk;
      }
      /**
       * Extracts the JWT claims present in the access token by first verifying the
       * JWT against the server's JSON Web Key Set endpoint
       * `/.well-known/jwks.json` which is often cached, resulting in significantly
       * faster responses. Prefer this method over {@link #getUser} which always
       * sends a request to the Auth server for each JWT.
       *
       * If the project is not using an asymmetric JWT signing key (like ECC or
       * RSA) it always sends a request to the Auth server (similar to {@link
       * #getUser}) to verify the JWT.
       *
       * @param jwt An optional specific JWT you wish to verify, not the one you
       *            can obtain from {@link #getSession}.
       * @param options Various additional options that allow you to customize the
       *                behavior of this method.
       *
       * @category Auth
       *
       * @remarks
       * - Parses the user's [access token](/docs/guides/auth/sessions#access-token-jwt-claims) as a [JSON Web Token (JWT)](/docs/guides/auth/jwts) and returns its components if valid and not expired.
       * - If your project is using asymmetric JWT signing keys, then the verification is done locally usually without a network request using the [WebCrypto API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Crypto_API).
       * - A network request is sent to your project's JWT signing key discovery endpoint `https://project-id.supabase.co/auth/v1/.well-known/jwks.json`, which is cached locally. If your environment is ephemeral, such as a Lambda function that is destroyed after every request, a network request will be sent for each new invocation. Supabase provides a network-edge cache providing fast responses for these situations.
       * - If the user's access token is about to expire when calling this function, the user's session will first be refreshed before validating the JWT.
       * - If your project is using a symmetric secret to sign the JWT, it always sends a request similar to `getUser()` to validate the JWT at the server before returning the decoded token. This is also used if the WebCrypto API is not available in the environment. Make sure you polyfill it in such situations.
       * - The returned claims can be customized per project using the [Custom Access Token Hook](/docs/guides/auth/auth-hooks/custom-access-token-hook).
       *
       * @example Get JWT claims, header and signature
       * ```js
       * const { data, error } = await supabase.auth.getClaims()
       * ```
       *
       * @exampleResponse Get JWT claims, header and signature
       * ```json
       * {
       *   "data": {
       *     "claims": {
       *       "aal": "aal1",
       *       "amr": [{
       *         "method": "email",
       *         "timestamp": 1715766000
       *       }],
       *       "app_metadata": {},
       *       "aud": "authenticated",
       *       "email": "example@email.com",
       *       "exp": 1715769600,
       *       "iat": 1715766000,
       *       "is_anonymous": false,
       *       "iss": "https://project-id.supabase.co/auth/v1",
       *       "phone": "+13334445555",
       *       "role": "authenticated",
       *       "session_id": "11111111-1111-1111-1111-111111111111",
       *       "sub": "11111111-1111-1111-1111-111111111111",
       *       "user_metadata": {}
       *     },
       *     "header": {
       *       "alg": "RS256",
       *       "typ": "JWT",
       *       "kid": "11111111-1111-1111-1111-111111111111"
       *     },
       *     "signature": [/** Uint8Array *\/],
       *   },
       *   "error": null
       * }
       * ```
       */
      async getClaims(jwt, options = {}) {
        try {
          let token = jwt;
          if (!token) {
            const { data, error } = await this.getSession();
            if (error || !data.session) {
              return this._returnResult({ data: null, error });
            }
            token = data.session.access_token;
          }
          const { header, payload, signature, raw: { header: rawHeader, payload: rawPayload } } = (0, helpers_1.decodeJWT)(token);
          if (!(options === null || options === void 0 ? void 0 : options.allowExpired)) {
            (0, helpers_1.validateExp)(payload.exp);
          }
          const signingKey = !header.alg || header.alg.startsWith("HS") || !header.kid || !("crypto" in globalThis && "subtle" in globalThis.crypto) ? null : await this.fetchJwk(header.kid, (options === null || options === void 0 ? void 0 : options.keys) ? { keys: options.keys } : options === null || options === void 0 ? void 0 : options.jwks);
          if (!signingKey) {
            const { error } = await this.getUser(token);
            if (error) {
              throw error;
            }
            return {
              data: {
                claims: payload,
                header,
                signature
              },
              error: null
            };
          }
          const algorithm = (0, helpers_1.getAlgorithm)(header.alg);
          const publicKey = await crypto.subtle.importKey("jwk", signingKey, algorithm, true, [
            "verify"
          ]);
          const isValid = await crypto.subtle.verify(algorithm, publicKey, signature, (0, base64url_1.stringToUint8Array)(`${rawHeader}.${rawPayload}`));
          if (!isValid) {
            throw new errors_1.AuthInvalidJwtError("Invalid JWT signature");
          }
          return {
            data: {
              claims: payload,
              header,
              signature
            },
            error: null
          };
        } catch (error) {
          if ((0, errors_1.isAuthError)(error)) {
            return this._returnResult({ data: null, error });
          }
          throw error;
        }
      }
    };
    GoTrueClient.nextInstanceID = {};
    exports2.default = GoTrueClient;
  }
});

// design/node_modules/@supabase/auth-js/dist/main/AuthAdminApi.js
var require_AuthAdminApi = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/AuthAdminApi.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    var tslib_1 = (init_tslib_es6(), __toCommonJS(tslib_es6_exports));
    var GoTrueAdminApi_1 = tslib_1.__importDefault(require_GoTrueAdminApi());
    var AuthAdminApi = GoTrueAdminApi_1.default;
    exports2.default = AuthAdminApi;
  }
});

// design/node_modules/@supabase/auth-js/dist/main/AuthClient.js
var require_AuthClient = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/AuthClient.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    var tslib_1 = (init_tslib_es6(), __toCommonJS(tslib_es6_exports));
    var GoTrueClient_1 = tslib_1.__importDefault(require_GoTrueClient());
    var AuthClient2 = GoTrueClient_1.default;
    exports2.default = AuthClient2;
  }
});

// design/node_modules/@supabase/auth-js/dist/main/index.js
var require_main3 = __commonJS({
  "design/node_modules/@supabase/auth-js/dist/main/index.js"(exports2) {
    "use strict";
    Object.defineProperty(exports2, "__esModule", { value: true });
    exports2.processLock = exports2.lockInternals = exports2.NavigatorLockAcquireTimeoutError = exports2.navigatorLock = exports2.AuthClient = exports2.AuthAdminApi = exports2.GoTrueClient = exports2.GoTrueAdminApi = void 0;
    var tslib_1 = (init_tslib_es6(), __toCommonJS(tslib_es6_exports));
    var GoTrueAdminApi_1 = tslib_1.__importDefault(require_GoTrueAdminApi());
    exports2.GoTrueAdminApi = GoTrueAdminApi_1.default;
    var GoTrueClient_1 = tslib_1.__importDefault(require_GoTrueClient());
    exports2.GoTrueClient = GoTrueClient_1.default;
    var AuthAdminApi_1 = tslib_1.__importDefault(require_AuthAdminApi());
    exports2.AuthAdminApi = AuthAdminApi_1.default;
    var AuthClient_1 = tslib_1.__importDefault(require_AuthClient());
    exports2.AuthClient = AuthClient_1.default;
    tslib_1.__exportStar(require_types2(), exports2);
    tslib_1.__exportStar(require_errors(), exports2);
    var locks_1 = require_locks();
    Object.defineProperty(exports2, "navigatorLock", { enumerable: true, get: function() {
      return locks_1.navigatorLock;
    } });
    Object.defineProperty(exports2, "NavigatorLockAcquireTimeoutError", { enumerable: true, get: function() {
      return locks_1.NavigatorLockAcquireTimeoutError;
    } });
    Object.defineProperty(exports2, "lockInternals", { enumerable: true, get: function() {
      return locks_1.internals;
    } });
    Object.defineProperty(exports2, "processLock", { enumerable: true, get: function() {
      return locks_1.processLock;
    } });
  }
});

// design/netlify/functions/api.ts
var api_exports = {};
__export(api_exports, {
  handler: () => handler
});
module.exports = __toCommonJS(api_exports);
var import_node_crypto = __toESM(require("crypto"), 1);

// design/node_modules/@supabase/supabase-js/dist/index.mjs
var dist_exports = {};
__export(dist_exports, {
  FunctionRegion: () => import_functions_js.FunctionRegion,
  FunctionsError: () => import_functions_js.FunctionsError,
  FunctionsFetchError: () => import_functions_js.FunctionsFetchError,
  FunctionsHttpError: () => import_functions_js.FunctionsHttpError,
  FunctionsRelayError: () => import_functions_js.FunctionsRelayError,
  PostgrestError: () => PostgrestError,
  StorageApiError: () => StorageApiError,
  SupabaseClient: () => SupabaseClient,
  createClient: () => createClient
});
var import_functions_js = __toESM(require_main(), 1);

// design/node_modules/@supabase/postgrest-js/dist/index.mjs
var DEFAULT_MAX_RETRIES = 3;
var getRetryDelay = (attemptIndex) => Math.min(1e3 * 2 ** attemptIndex, 3e4);
var RETRYABLE_STATUS_CODES = [520, 503];
var RETRYABLE_METHODS = [
  "GET",
  "HEAD",
  "OPTIONS"
];
var PostgrestError = class extends Error {
  /**
  * @example
  * ```ts
  * import PostgrestError from '@supabase/postgrest-js'
  *
  * throw new PostgrestError({
  *   message: 'Row level security prevented the request',
  *   details: 'RLS denied the insert',
  *   hint: 'Check your policies',
  *   code: 'PGRST301',
  * })
  * ```
  */
  constructor(context) {
    super(context.message);
    this.name = "PostgrestError";
    this.details = context.details;
    this.hint = context.hint;
    this.code = context.code;
  }
  toJSON() {
    return {
      name: this.name,
      message: this.message,
      details: this.details,
      hint: this.hint,
      code: this.code
    };
  }
};
function sleep(ms, signal) {
  return new Promise((resolve) => {
    if (signal === null || signal === void 0 ? void 0 : signal.aborted) {
      resolve();
      return;
    }
    const id = setTimeout(() => {
      signal === null || signal === void 0 || signal.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    function onAbort() {
      clearTimeout(id);
      resolve();
    }
    signal === null || signal === void 0 || signal.addEventListener("abort", onAbort);
  });
}
function shouldRetry(method, status, attemptCount, retryEnabled) {
  if (!retryEnabled || attemptCount >= DEFAULT_MAX_RETRIES) return false;
  if (!RETRYABLE_METHODS.includes(method)) return false;
  if (!RETRYABLE_STATUS_CODES.includes(status)) return false;
  return true;
}
var PostgrestBuilder = class {
  /**
  * Creates a builder configured for a specific PostgREST request.
  *
  * @example Using supabase-js (recommended)
  * ```ts
  * import { createClient } from '@supabase/supabase-js'
  *
  * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key')
  * const { data, error } = await supabase.from('users').select('*')
  * ```
  *
  * @category Database
  *
  * @example Standalone import for bundle-sensitive environments
  * ```ts
  * import { PostgrestQueryBuilder } from '@supabase/postgrest-js'
  *
  * const builder = new PostgrestQueryBuilder(
  *   new URL('https://xyzcompany.supabase.co/rest/v1/users'),
  *   { headers: new Headers({ apikey: 'publishable-or-anon-key' }) }
  * )
  * ```
  */
  constructor(builder) {
    var _builder$shouldThrowO, _builder$isMaybeSingl, _builder$shouldStripN, _builder$urlLengthLim, _builder$retry;
    this.shouldThrowOnError = false;
    this.retryEnabled = true;
    this.method = builder.method;
    this.url = builder.url;
    this.headers = new Headers(builder.headers);
    this.schema = builder.schema;
    this.body = builder.body;
    this.shouldThrowOnError = (_builder$shouldThrowO = builder.shouldThrowOnError) !== null && _builder$shouldThrowO !== void 0 ? _builder$shouldThrowO : false;
    this.signal = builder.signal;
    this.isMaybeSingle = (_builder$isMaybeSingl = builder.isMaybeSingle) !== null && _builder$isMaybeSingl !== void 0 ? _builder$isMaybeSingl : false;
    this.shouldStripNulls = (_builder$shouldStripN = builder.shouldStripNulls) !== null && _builder$shouldStripN !== void 0 ? _builder$shouldStripN : false;
    this.urlLengthLimit = (_builder$urlLengthLim = builder.urlLengthLimit) !== null && _builder$urlLengthLim !== void 0 ? _builder$urlLengthLim : 8e3;
    this.retryEnabled = (_builder$retry = builder.retry) !== null && _builder$retry !== void 0 ? _builder$retry : true;
    if (builder.fetch) this.fetch = builder.fetch;
    else this.fetch = fetch;
  }
  /**
  * If there's an error with the query, throwOnError will reject the promise by
  * throwing the error instead of returning it as part of a successful response.
  *
  * {@link https://github.com/supabase/supabase-js/issues/92}
  *
  * @category Database
  */
  throwOnError() {
    this.shouldThrowOnError = true;
    return this;
  }
  /**
  * Strip null values from the response data. Properties with `null` values
  * will be omitted from the returned JSON objects.
  *
  * Requires PostgREST 11.2.0+.
  *
  * {@link https://docs.postgrest.org/en/stable/references/api/resource_representation.html#stripped-nulls}
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .stripNulls()
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text, bio text);
  *
  * insert into
  *   characters (id, name, bio)
  * values
  *   (1, 'Luke', null),
  *   (2, 'Leia', 'Princess of Alderaan');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "Luke"
  *     },
  *     {
  *       "id": 2,
  *       "name": "Leia",
  *       "bio": "Princess of Alderaan"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  stripNulls() {
    if (this.headers.get("Accept") === "text/csv") throw new Error("stripNulls() cannot be used with csv()");
    this.shouldStripNulls = true;
    return this;
  }
  /**
  * Set an HTTP header for the request.
  *
  * @category Database
  */
  setHeader(name, value) {
    this.headers = new Headers(this.headers);
    this.headers.set(name, value);
    return this;
  }
  /**
  * @category Database
  *
  * Configure retry behavior for this request.
  *
  * By default, retries are enabled for idempotent requests (GET, HEAD, OPTIONS)
  * that fail with network errors or specific HTTP status codes (503, 520).
  * Retries use exponential backoff (1s, 2s, 4s) with a maximum of 3 attempts.
  *
  * @param enabled - Whether to enable retries for this request
  *
  * @example
  * ```ts
  * // Disable retries for a specific query
  * const { data, error } = await supabase
  *   .from('users')
  *   .select()
  *   .retry(false)
  * ```
  */
  retry(enabled) {
    this.retryEnabled = enabled;
    return this;
  }
  then(onfulfilled, onrejected) {
    var _this = this;
    if (this.schema === void 0) {
    } else if (["GET", "HEAD"].includes(this.method)) this.headers.set("Accept-Profile", this.schema);
    else this.headers.set("Content-Profile", this.schema);
    if (this.method !== "GET" && this.method !== "HEAD") this.headers.set("Content-Type", "application/json");
    if (this.shouldStripNulls) {
      const currentAccept = this.headers.get("Accept");
      if (currentAccept === "application/vnd.pgrst.object+json") this.headers.set("Accept", "application/vnd.pgrst.object+json;nulls=stripped");
      else if (!currentAccept || currentAccept === "application/json") this.headers.set("Accept", "application/vnd.pgrst.array+json;nulls=stripped");
    }
    const _fetch = this.fetch;
    const executeWithRetry = async () => {
      let attemptCount = 0;
      while (true) {
        const requestHeaders = new Headers(_this.headers);
        if (attemptCount > 0) requestHeaders.set("X-Retry-Count", String(attemptCount));
        let res$1;
        try {
          res$1 = await _fetch(_this.url.toString(), {
            method: _this.method,
            headers: requestHeaders,
            body: JSON.stringify(_this.body, (_, value) => typeof value === "bigint" ? value.toString() : value),
            signal: _this.signal
          });
        } catch (fetchError) {
          if ((fetchError === null || fetchError === void 0 ? void 0 : fetchError.name) === "AbortError" || (fetchError === null || fetchError === void 0 ? void 0 : fetchError.code) === "ABORT_ERR") throw fetchError;
          if (!RETRYABLE_METHODS.includes(_this.method)) throw fetchError;
          if (_this.retryEnabled && attemptCount < DEFAULT_MAX_RETRIES) {
            const delay = getRetryDelay(attemptCount);
            attemptCount++;
            await sleep(delay, _this.signal);
            continue;
          }
          throw fetchError;
        }
        if (shouldRetry(_this.method, res$1.status, attemptCount, _this.retryEnabled)) {
          var _res$headers$get, _res$headers;
          const retryAfterHeader = (_res$headers$get = (_res$headers = res$1.headers) === null || _res$headers === void 0 ? void 0 : _res$headers.get("Retry-After")) !== null && _res$headers$get !== void 0 ? _res$headers$get : null;
          const delay = retryAfterHeader !== null ? Math.max(0, parseInt(retryAfterHeader, 10) || 0) * 1e3 : getRetryDelay(attemptCount);
          await res$1.text();
          attemptCount++;
          await sleep(delay, _this.signal);
          continue;
        }
        return await _this.processResponse(res$1);
      }
    };
    let res = executeWithRetry();
    if (!this.shouldThrowOnError) res = res.catch((fetchError) => {
      var _fetchError$name2;
      let errorDetails = "";
      let hint = "";
      let code = "";
      const cause = fetchError === null || fetchError === void 0 ? void 0 : fetchError.cause;
      if (cause) {
        var _cause$message, _cause$code, _fetchError$name, _cause$name;
        const causeMessage = (_cause$message = cause === null || cause === void 0 ? void 0 : cause.message) !== null && _cause$message !== void 0 ? _cause$message : "";
        const causeCode = (_cause$code = cause === null || cause === void 0 ? void 0 : cause.code) !== null && _cause$code !== void 0 ? _cause$code : "";
        errorDetails = `${(_fetchError$name = fetchError === null || fetchError === void 0 ? void 0 : fetchError.name) !== null && _fetchError$name !== void 0 ? _fetchError$name : "FetchError"}: ${fetchError === null || fetchError === void 0 ? void 0 : fetchError.message}`;
        errorDetails += `

Caused by: ${(_cause$name = cause === null || cause === void 0 ? void 0 : cause.name) !== null && _cause$name !== void 0 ? _cause$name : "Error"}: ${causeMessage}`;
        if (causeCode) errorDetails += ` (${causeCode})`;
        if (cause === null || cause === void 0 ? void 0 : cause.stack) errorDetails += `
${cause.stack}`;
      } else {
        var _fetchError$stack;
        errorDetails = (_fetchError$stack = fetchError === null || fetchError === void 0 ? void 0 : fetchError.stack) !== null && _fetchError$stack !== void 0 ? _fetchError$stack : "";
      }
      const urlLength = this.url.toString().length;
      if ((fetchError === null || fetchError === void 0 ? void 0 : fetchError.name) === "AbortError" || (fetchError === null || fetchError === void 0 ? void 0 : fetchError.code) === "ABORT_ERR") {
        code = "";
        hint = "Request was aborted (timeout or manual cancellation)";
        if (urlLength > this.urlLengthLimit) hint += `. Note: Your request URL is ${urlLength} characters, which may exceed server limits. If selecting many fields, consider using views. If filtering with large arrays (e.g., .in('id', [many IDs])), consider using an RPC function to pass values server-side.`;
      } else if ((cause === null || cause === void 0 ? void 0 : cause.name) === "HeadersOverflowError" || (cause === null || cause === void 0 ? void 0 : cause.code) === "UND_ERR_HEADERS_OVERFLOW") {
        code = "";
        hint = "HTTP headers exceeded server limits (typically 16KB)";
        if (urlLength > this.urlLengthLimit) hint += `. Your request URL is ${urlLength} characters. If selecting many fields, consider using views. If filtering with large arrays (e.g., .in('id', [200+ IDs])), consider using an RPC function instead.`;
      }
      return {
        success: false,
        error: {
          message: `${(_fetchError$name2 = fetchError === null || fetchError === void 0 ? void 0 : fetchError.name) !== null && _fetchError$name2 !== void 0 ? _fetchError$name2 : "FetchError"}: ${fetchError === null || fetchError === void 0 ? void 0 : fetchError.message}`,
          details: errorDetails,
          hint,
          code
        },
        data: null,
        count: null,
        status: 0,
        statusText: ""
      };
    });
    return res.then(onfulfilled, onrejected);
  }
  /**
  * Process a fetch response and return the standardized postgrest response.
  */
  async processResponse(res) {
    var _this2 = this;
    let error = null;
    let data = null;
    let count = null;
    let status = res.status;
    let statusText = res.statusText;
    if (res.ok) {
      var _this$headers$get2, _res$headers$get2;
      if (_this2.method !== "HEAD") {
        var _this$headers$get;
        const body = await res.text();
        if (body === "") {
        } else if (_this2.headers.get("Accept") === "text/csv") data = body;
        else if (_this2.headers.get("Accept") && ((_this$headers$get = _this2.headers.get("Accept")) === null || _this$headers$get === void 0 ? void 0 : _this$headers$get.includes("application/vnd.pgrst.plan+text"))) data = body;
        else data = JSON.parse(body);
      }
      const countHeader = (_this$headers$get2 = _this2.headers.get("Prefer")) === null || _this$headers$get2 === void 0 ? void 0 : _this$headers$get2.match(/count=(exact|planned|estimated)/);
      const contentRange = (_res$headers$get2 = res.headers.get("content-range")) === null || _res$headers$get2 === void 0 ? void 0 : _res$headers$get2.split("/");
      if (countHeader && contentRange && contentRange.length > 1) count = parseInt(contentRange[1]);
      if (_this2.isMaybeSingle && Array.isArray(data)) if (data.length > 1) {
        error = {
          code: "PGRST116",
          details: `Results contain ${data.length} rows, application/vnd.pgrst.object+json requires 1 row`,
          hint: null,
          message: "JSON object requested, multiple (or no) rows returned"
        };
        data = null;
        count = null;
        status = 406;
        statusText = "Not Acceptable";
      } else if (data.length === 1) data = data[0];
      else data = null;
    } else {
      const body = await res.text();
      try {
        error = JSON.parse(body);
        if (Array.isArray(error) && res.status === 404) {
          data = [];
          error = null;
          status = 200;
          statusText = "OK";
        }
      } catch (_unused) {
        if (res.status === 404 && body === "") {
          status = 204;
          statusText = "No Content";
        } else error = { message: body };
      }
      if (error && _this2.shouldThrowOnError) throw new PostgrestError(error);
    }
    return {
      success: error === null,
      error,
      data,
      count,
      status,
      statusText
    };
  }
  /**
  * Override the type of the returned `data`.
  *
  * @typeParam NewResult - The new result type to override with
  * @deprecated Use overrideTypes<yourType, { merge: false }>() method at the end of your call chain instead
  *
  * @category Database
  */
  returns() {
    return this;
  }
  /**
  * Override the type of the returned `data` field in the response.
  *
  * @typeParam NewResult - The new type to cast the response data to
  * @typeParam Options - Optional type configuration (defaults to { merge: true })
  * @typeParam Options.merge - When true, merges the new type with existing return type. When false, replaces the existing types entirely (defaults to true)
  * @example
  * ```typescript
  * // Merge with existing types (default behavior)
  * const query = supabase
  *   .from('users')
  *   .select()
  *   .overrideTypes<{ custom_field: string }>()
  *
  * // Replace existing types completely
  * const replaceQuery = supabase
  *   .from('users')
  *   .select()
  *   .overrideTypes<{ id: number; name: string }, { merge: false }>()
  * ```
  * @returns A PostgrestBuilder instance with the new type
  *
  * @category Database
  *
  * @example Complete Override type of successful response
  * ```ts
  * const { data } = await supabase
  *   .from('countries')
  *   .select()
  *   .overrideTypes<Array<MyType>, { merge: false }>()
  * ```
  *
  * @exampleResponse Complete Override type of successful response
  * ```ts
  * let x: typeof data // MyType[]
  * ```
  *
  * @example Complete Override type of object response
  * ```ts
  * const { data } = await supabase
  *   .from('countries')
  *   .select()
  *   .maybeSingle()
  *   .overrideTypes<MyType, { merge: false }>()
  * ```
  *
  * @exampleResponse Complete Override type of object response
  * ```ts
  * let x: typeof data // MyType | null
  * ```
  *
  * @example Partial Override type of successful response
  * ```ts
  * const { data } = await supabase
  *   .from('countries')
  *   .select()
  *   .overrideTypes<Array<{ status: "A" | "B" }>>()
  * ```
  *
  * @exampleResponse Partial Override type of successful response
  * ```ts
  * let x: typeof data // Array<CountryRowProperties & { status: "A" | "B" }>
  * ```
  *
  * @example Partial Override type of object response
  * ```ts
  * const { data } = await supabase
  *   .from('countries')
  *   .select()
  *   .maybeSingle()
  *   .overrideTypes<{ status: "A" | "B" }>()
  * ```
  *
  * @exampleResponse Partial Override type of object response
  * ```ts
  * let x: typeof data // CountryRowProperties & { status: "A" | "B" } | null
  * ```
  *
  * @example Example 5
  * ```typescript
  * // Merge with existing types (default behavior)
  * const query = supabase
  *   .from('users')
  *   .select()
  *   .overrideTypes<{ custom_field: string }>()
  *
  * // Replace existing types completely
  * const replaceQuery = supabase
  *   .from('users')
  *   .select()
  *   .overrideTypes<{ id: number; name: string }, { merge: false }>()
  * ```
  */
  overrideTypes() {
    return this;
  }
};
var PostgrestTransformBuilder = class extends PostgrestBuilder {
  /**
  * Perform a SELECT on the query result.
  *
  * By default, `.insert()`, `.update()`, `.upsert()`, and `.delete()` do not
  * return modified rows. By calling this method, modified rows are returned in
  * `data`.
  *
  * @param columns - The columns to retrieve, separated by commas
  *
  * @category Database
  *
  * @example With `upsert()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .upsert({ id: 1, name: 'Han Solo' })
  *   .select()
  * ```
  *
  * @exampleSql With `upsert()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Han');
  * ```
  *
  * @exampleResponse With `upsert()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "Han Solo"
  *     }
  *   ],
  *   "status": 201,
  *   "statusText": "Created"
  * }
  * ```
  */
  select(columns) {
    let quoted = false;
    const cleanedColumns = (columns !== null && columns !== void 0 ? columns : "*").split("").map((c) => {
      if (/\s/.test(c) && !quoted) return "";
      if (c === '"') quoted = !quoted;
      return c;
    }).join("");
    this.url.searchParams.set("select", cleanedColumns);
    this.headers.append("Prefer", "return=representation");
    return this;
  }
  /**
  * Order the query result by `column`.
  *
  * You can call this method multiple times to order by multiple columns.
  *
  * You can order referenced tables, but it only affects the ordering of the
  * parent table if you use `!inner` in the query.
  *
  * @param column - The column to order by
  * @param options - Named parameters
  * @param options.ascending - If `true`, the result will be in ascending order
  * @param options.nullsFirst - If `true`, `null`s appear first. If `false`,
  * `null`s appear last.
  * @param options.referencedTable - Set this to order a referenced table by
  * its columns
  * @param options.foreignTable - Deprecated, use `options.referencedTable`
  * instead
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select('id, name')
  *   .order('id', { ascending: false })
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 3,
  *       "name": "Han"
  *     },
  *     {
  *       "id": 2,
  *       "name": "Leia"
  *     },
  *     {
  *       "id": 1,
  *       "name": "Luke"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription On a referenced table
  * Ordering with `referencedTable` doesn't affect the ordering of the
  * parent table.
  *
  * @example On a referenced table
  * ```ts
  *   const { data, error } = await supabase
  *     .from('orchestral_sections')
  *     .select(`
  *       name,
  *       instruments (
  *         name
  *       )
  *     `)
  *     .order('name', { referencedTable: 'instruments', ascending: false })
  *
  * ```
  *
  * @exampleSql On a referenced table
  * ```sql
  * create table
  *   orchestral_sections (id int8 primary key, name text);
  * create table
  *   instruments (
  *     id int8 primary key,
  *     section_id int8 not null references orchestral_sections,
  *     name text
  *   );
  *
  * insert into
  *   orchestral_sections (id, name)
  * values
  *   (1, 'strings'),
  *   (2, 'woodwinds');
  * insert into
  *   instruments (id, section_id, name)
  * values
  *   (1, 1, 'harp'),
  *   (2, 1, 'violin');
  * ```
  *
  * @exampleResponse On a referenced table
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "strings",
  *       "instruments": [
  *         {
  *           "name": "violin"
  *         },
  *         {
  *           "name": "harp"
  *         }
  *       ]
  *     },
  *     {
  *       "name": "woodwinds",
  *       "instruments": []
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription Order parent table by a referenced table
  * Ordering with `referenced_table(col)` affects the ordering of the
  * parent table.
  *
  * @example Order parent table by a referenced table
  * ```ts
  *   const { data, error } = await supabase
  *     .from('instruments')
  *     .select(`
  *       name,
  *       section:orchestral_sections (
  *         name
  *       )
  *     `)
  *     .order('section(name)', { ascending: true })
  *
  * ```
  *
  * @exampleSql Order parent table by a referenced table
  * ```sql
  * create table
  *   orchestral_sections (id int8 primary key, name text);
  * create table
  *   instruments (
  *     id int8 primary key,
  *     section_id int8 not null references orchestral_sections,
  *     name text
  *   );
  *
  * insert into
  *   orchestral_sections (id, name)
  * values
  *   (1, 'strings'),
  *   (2, 'woodwinds');
  * insert into
  *   instruments (id, section_id, name)
  * values
  *   (1, 2, 'flute'),
  *   (2, 1, 'violin');
  * ```
  *
  * @exampleResponse Order parent table by a referenced table
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "violin",
  *       "orchestral_sections": {"name": "strings"}
  *     },
  *     {
  *       "name": "flute",
  *       "orchestral_sections": {"name": "woodwinds"}
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  order(column, { ascending = true, nullsFirst, foreignTable, referencedTable = foreignTable } = {}) {
    const key = referencedTable ? `${referencedTable}.order` : "order";
    const existingOrder = this.url.searchParams.get(key);
    this.url.searchParams.set(key, `${existingOrder ? `${existingOrder},` : ""}${column}.${ascending ? "asc" : "desc"}${nullsFirst === void 0 ? "" : nullsFirst ? ".nullsfirst" : ".nullslast"}`);
    return this;
  }
  /**
  * Limit the query result by `count`.
  *
  * @param count - The maximum number of rows to return
  * @param options - Named parameters
  * @param options.referencedTable - Set this to limit rows of referenced
  * tables instead of the parent table
  * @param options.foreignTable - Deprecated, use `options.referencedTable`
  * instead
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select('name')
  *   .limit(1)
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "Luke"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @example On a referenced table
  * ```ts
  * const { data, error } = await supabase
  *   .from('orchestral_sections')
  *   .select(`
  *     name,
  *     instruments (
  *       name
  *     )
  *   `)
  *   .limit(1, { referencedTable: 'instruments' })
  * ```
  *
  * @exampleSql On a referenced table
  * ```sql
  * create table
  *   orchestral_sections (id int8 primary key, name text);
  * create table
  *   instruments (
  *     id int8 primary key,
  *     section_id int8 not null references orchestral_sections,
  *     name text
  *   );
  *
  * insert into
  *   orchestral_sections (id, name)
  * values
  *   (1, 'strings');
  * insert into
  *   instruments (id, section_id, name)
  * values
  *   (1, 1, 'harp'),
  *   (2, 1, 'violin');
  * ```
  *
  * @exampleResponse On a referenced table
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "strings",
  *       "instruments": [
  *         {
  *           "name": "violin"
  *         }
  *       ]
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  limit(count, { foreignTable, referencedTable = foreignTable } = {}) {
    const key = typeof referencedTable === "undefined" ? "limit" : `${referencedTable}.limit`;
    this.url.searchParams.set(key, `${count}`);
    return this;
  }
  /**
  * Limit the query result by starting at an offset `from` and ending at the offset `to`.
  * Only records within this range are returned.
  * This respects the query order and if there is no order clause the range could behave unexpectedly.
  * The `from` and `to` values are 0-based and inclusive: `range(1, 3)` will include the second, third
  * and fourth rows of the query.
  *
  * @param from - The starting index from which to limit the result
  * @param to - The last index to which to limit the result
  * @param options - Named parameters
  * @param options.referencedTable - Set this to limit rows of referenced
  * tables instead of the parent table
  * @param options.foreignTable - Deprecated, use `options.referencedTable`
  * instead
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select('name')
  *   .range(0, 1)
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "Luke"
  *     },
  *     {
  *       "name": "Leia"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  range(from, to, { foreignTable, referencedTable = foreignTable } = {}) {
    const keyOffset = typeof referencedTable === "undefined" ? "offset" : `${referencedTable}.offset`;
    const keyLimit = typeof referencedTable === "undefined" ? "limit" : `${referencedTable}.limit`;
    this.url.searchParams.set(keyOffset, `${from}`);
    this.url.searchParams.set(keyLimit, `${to - from + 1}`);
    return this;
  }
  /**
  * Set the AbortSignal for the fetch request.
  *
  * @param signal - The AbortSignal to use for the fetch request
  *
  * @category Database
  *
  * @remarks
  * You can use this to set a timeout for the request.
  *
  * @exampleDescription Aborting requests in-flight
  * You can use an [`AbortController`](https://developer.mozilla.org/en-US/docs/Web/API/AbortController) to abort requests.
  * Note that `status` and `statusText` don't mean anything for aborted requests as the request wasn't fulfilled.
  *
  * @example Aborting requests in-flight
  * ```ts
  * const ac = new AbortController()
  *
  * const { data, error } = await supabase
  *   .from('very_big_table')
  *   .select()
  *   .abortSignal(ac.signal)
  *
  * // Abort the request after 100 ms
  * setTimeout(() => ac.abort(), 100)
  * ```
  *
  * @exampleResponse Aborting requests in-flight
  * ```json
  *   {
  *     "error": {
  *       "message": "AbortError: The user aborted a request.",
  *       "details": "",
  *       "hint": "The request was aborted locally via the provided AbortSignal.",
  *       "code": ""
  *     },
  *     "status": 0,
  *     "statusText": ""
  *   }
  *
  * ```
  *
  * @example Set a timeout
  * ```ts
  * const { data, error } = await supabase
  *   .from('very_big_table')
  *   .select()
  *   .abortSignal(AbortSignal.timeout(1000 /* ms *\/))
  * ```
  *
  * @exampleResponse Set a timeout
  * ```json
  *   {
  *     "error": {
  *       "message": "FetchError: The user aborted a request.",
  *       "details": "",
  *       "hint": "",
  *       "code": ""
  *     },
  *     "status": 400,
  *     "statusText": "Bad Request"
  *   }
  *
  * ```
  */
  abortSignal(signal) {
    this.signal = signal;
    return this;
  }
  /**
  * Return `data` as a single object instead of an array of objects.
  *
  * Query result must be one row (e.g. using `.limit(1)`), otherwise this
  * returns an error.
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select('name')
  *   .limit(1)
  *   .single()
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": {
  *     "name": "Luke"
  *   },
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  single() {
    this.headers.set("Accept", "application/vnd.pgrst.object+json");
    return this;
  }
  /**
  * Return `data` as a single object instead of an array of objects.
  *
  * Query result must be zero or one row (e.g. using `.limit(1)`), otherwise
  * this returns an error.
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .eq('name', 'Katniss')
  *   .maybeSingle()
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  maybeSingle() {
    this.isMaybeSingle = true;
    return this;
  }
  /**
  * Return `data` as a string in CSV format.
  *
  * @category Database
  *
  * @exampleDescription Return data as CSV
  * By default, the data is returned in JSON format, but can also be returned as Comma Separated Values.
  *
  * @example Return data as CSV
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .csv()
  * ```
  *
  * @exampleSql Return data as CSV
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse Return data as CSV
  * ```json
  * {
  *   "data": "id,name\n1,Luke\n2,Leia\n3,Han",
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  csv() {
    this.headers.set("Accept", "text/csv");
    return this;
  }
  /**
  * Return `data` as an object in [GeoJSON](https://geojson.org) format.
  *
  * @category Database
  */
  geojson() {
    this.headers.set("Accept", "application/geo+json");
    return this;
  }
  /**
  * Return `data` as the EXPLAIN plan for the query.
  *
  * You need to enable the
  * [db_plan_enabled](https://supabase.com/docs/guides/database/debugging-performance#enabling-explain)
  * setting before using this method.
  *
  * @param options - Named parameters
  *
  * @param options.analyze - If `true`, the query will be executed and the
  * actual run time will be returned
  *
  * @param options.verbose - If `true`, the query identifier will be returned
  * and `data` will include the output columns of the query
  *
  * @param options.settings - If `true`, include information on configuration
  * parameters that affect query planning
  *
  * @param options.buffers - If `true`, include information on buffer usage
  *
  * @param options.wal - If `true`, include information on WAL record generation
  *
  * @param options.format - The format of the output, can be `"text"` (default)
  * or `"json"`
  *
  * @category Database
  *
  * @exampleDescription Get the execution plan
  * By default, the data is returned in TEXT format, but can also be returned as JSON by using the `format` parameter.
  *
  * @example Get the execution plan
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .explain()
  * ```
  *
  * @exampleSql Get the execution plan
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse Get the execution plan
  * ```js
  * Aggregate  (cost=33.34..33.36 rows=1 width=112)
  *   ->  Limit  (cost=0.00..18.33 rows=1000 width=40)
  *         ->  Seq Scan on characters  (cost=0.00..22.00 rows=1200 width=40)
  * ```
  *
  * @exampleDescription Get the execution plan with analyze and verbose
  * By default, the data is returned in TEXT format, but can also be returned as JSON by using the `format` parameter.
  *
  * @example Get the execution plan with analyze and verbose
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .explain({analyze:true,verbose:true})
  * ```
  *
  * @exampleSql Get the execution plan with analyze and verbose
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse Get the execution plan with analyze and verbose
  * ```js
  * Aggregate  (cost=33.34..33.36 rows=1 width=112) (actual time=0.041..0.041 rows=1 loops=1)
  *   Output: NULL::bigint, count(ROW(characters.id, characters.name)), COALESCE(json_agg(ROW(characters.id, characters.name)), '[]'::json), NULLIF(current_setting('response.headers'::text, true), ''::text), NULLIF(current_setting('response.status'::text, true), ''::text)
  *   ->  Limit  (cost=0.00..18.33 rows=1000 width=40) (actual time=0.005..0.006 rows=3 loops=1)
  *         Output: characters.id, characters.name
  *         ->  Seq Scan on public.characters  (cost=0.00..22.00 rows=1200 width=40) (actual time=0.004..0.005 rows=3 loops=1)
  *               Output: characters.id, characters.name
  * Query Identifier: -4730654291623321173
  * Planning Time: 0.407 ms
  * Execution Time: 0.119 ms
  * ```
  */
  explain({ analyze = false, verbose = false, settings = false, buffers = false, wal = false, format = "text" } = {}) {
    var _this$headers$get;
    const options = [
      analyze ? "analyze" : null,
      verbose ? "verbose" : null,
      settings ? "settings" : null,
      buffers ? "buffers" : null,
      wal ? "wal" : null
    ].filter(Boolean).join("|");
    const forMediatype = (_this$headers$get = this.headers.get("Accept")) !== null && _this$headers$get !== void 0 ? _this$headers$get : "application/json";
    this.headers.set("Accept", `application/vnd.pgrst.plan+${format}; for="${forMediatype}"; options=${options};`);
    if (format === "json") return this;
    else return this;
  }
  /**
  * Rollback the query.
  *
  * `data` will still be returned, but the query is not committed.
  *
  * @category Database
  */
  rollback() {
    this.headers.append("Prefer", "tx=rollback");
    return this;
  }
  /**
  * Override the type of the returned `data`.
  *
  * @typeParam NewResult - The new result type to override with
  * @deprecated Use overrideTypes<yourType, { merge: false }>() method at the end of your call chain instead
  *
  * @category Database
  *
  * @remarks
  * - Deprecated: use overrideTypes method instead
  *
  * @example Override type of successful response
  * ```ts
  * const { data } = await supabase
  *   .from('countries')
  *   .select()
  *   .returns<Array<MyType>>()
  * ```
  *
  * @exampleResponse Override type of successful response
  * ```js
  * let x: typeof data // MyType[]
  * ```
  *
  * @example Override type of object response
  * ```ts
  * const { data } = await supabase
  *   .from('countries')
  *   .select()
  *   .maybeSingle()
  *   .returns<MyType>()
  * ```
  *
  * @exampleResponse Override type of object response
  * ```js
  * let x: typeof data // MyType | null
  * ```
  */
  returns() {
    return this;
  }
  /**
  * Set the maximum number of rows that can be affected by the query.
  * Only available in PostgREST v13+ and only works with PATCH and DELETE methods.
  *
  * @param value - The maximum number of rows that can be affected
  *
  * @category Database
  */
  maxAffected(value) {
    this.headers.append("Prefer", "handling=strict");
    this.headers.append("Prefer", `max-affected=${value}`);
    return this;
  }
};
var PostgrestReservedCharsRegexp = /* @__PURE__ */ new RegExp("[,()]");
var PostgrestFilterBuilder = class extends PostgrestTransformBuilder {
  /**
  * Match only rows where `column` is equal to `value`.
  *
  * To check if the value of `column` is NULL, you should use `.is()` instead.
  *
  * @param column - The column to filter on
  * @param value - The value to filter with
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .eq('name', 'Leia')
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 2,
  *       "name": "Leia"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  eq(column, value) {
    this.url.searchParams.append(column, `eq.${value}`);
    return this;
  }
  /**
  * Match only rows where `column` is not equal to `value`.
  *
  * @param column - The column to filter on
  * @param value - The value to filter with
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .neq('name', 'Leia')
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "Luke"
  *     },
  *     {
  *       "id": 3,
  *       "name": "Han"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  neq(column, value) {
    this.url.searchParams.append(column, `neq.${value}`);
    return this;
  }
  /**
  * Match only rows where `column` is greater than `value`.
  *
  * @param column - The column to filter on
  * @param value - The value to filter with
  *
  * @category Database
  *
  * @exampleDescription With `select()`
  * When using [reserved words](https://www.postgresql.org/docs/current/sql-keywords-appendix.html) for column names you need
  * to add double quotes e.g. `.gt('"order"', 2)`
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .gt('id', 2)
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 3,
  *       "name": "Han"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  gt(column, value) {
    this.url.searchParams.append(column, `gt.${value}`);
    return this;
  }
  /**
  * Match only rows where `column` is greater than or equal to `value`.
  *
  * @param column - The column to filter on
  * @param value - The value to filter with
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .gte('id', 2)
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 2,
  *       "name": "Leia"
  *     },
  *     {
  *       "id": 3,
  *       "name": "Han"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  gte(column, value) {
    this.url.searchParams.append(column, `gte.${value}`);
    return this;
  }
  /**
  * Match only rows where `column` is less than `value`.
  *
  * @param column - The column to filter on
  * @param value - The value to filter with
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .lt('id', 2)
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "Luke"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  lt(column, value) {
    this.url.searchParams.append(column, `lt.${value}`);
    return this;
  }
  /**
  * Match only rows where `column` is less than or equal to `value`.
  *
  * @param column - The column to filter on
  * @param value - The value to filter with
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .lte('id', 2)
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "Luke"
  *     },
  *     {
  *       "id": 2,
  *       "name": "Leia"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  lte(column, value) {
    this.url.searchParams.append(column, `lte.${value}`);
    return this;
  }
  /**
  * Match only rows where `column` matches `pattern` case-sensitively.
  *
  * @param column - The column to filter on
  * @param pattern - The pattern to match with
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .like('name', '%Lu%')
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "Luke"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  like(column, pattern) {
    this.url.searchParams.append(column, `like.${pattern}`);
    return this;
  }
  /**
  * Match only rows where `column` matches all of `patterns` case-sensitively.
  *
  * @param column - The column to filter on
  * @param patterns - The patterns to match with
  *
  * @category Database
  */
  likeAllOf(column, patterns) {
    this.url.searchParams.append(column, `like(all).{${patterns.join(",")}}`);
    return this;
  }
  /**
  * Match only rows where `column` matches any of `patterns` case-sensitively.
  *
  * @param column - The column to filter on
  * @param patterns - The patterns to match with
  *
  * @category Database
  */
  likeAnyOf(column, patterns) {
    this.url.searchParams.append(column, `like(any).{${patterns.join(",")}}`);
    return this;
  }
  /**
  * Match only rows where `column` matches `pattern` case-insensitively.
  *
  * @param column - The column to filter on
  * @param pattern - The pattern to match with
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .ilike('name', '%lu%')
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "Luke"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  ilike(column, pattern) {
    this.url.searchParams.append(column, `ilike.${pattern}`);
    return this;
  }
  /**
  * Match only rows where `column` matches all of `patterns` case-insensitively.
  *
  * @param column - The column to filter on
  * @param patterns - The patterns to match with
  *
  * @category Database
  */
  ilikeAllOf(column, patterns) {
    this.url.searchParams.append(column, `ilike(all).{${patterns.join(",")}}`);
    return this;
  }
  /**
  * Match only rows where `column` matches any of `patterns` case-insensitively.
  *
  * @param column - The column to filter on
  * @param patterns - The patterns to match with
  *
  * @category Database
  */
  ilikeAnyOf(column, patterns) {
    this.url.searchParams.append(column, `ilike(any).{${patterns.join(",")}}`);
    return this;
  }
  /**
  * Match only rows where `column` matches the PostgreSQL regex `pattern`
  * case-sensitively (using the `~` operator).
  *
  * @param column - The column to filter on
  * @param pattern - The PostgreSQL regular expression pattern to match with
  */
  regexMatch(column, pattern) {
    this.url.searchParams.append(column, `match.${pattern}`);
    return this;
  }
  /**
  * Match only rows where `column` matches the PostgreSQL regex `pattern`
  * case-insensitively (using the `~*` operator).
  *
  * @param column - The column to filter on
  * @param pattern - The PostgreSQL regular expression pattern to match with
  */
  regexIMatch(column, pattern) {
    this.url.searchParams.append(column, `imatch.${pattern}`);
    return this;
  }
  /**
  * Match only rows where `column` IS `value`.
  *
  * For non-boolean columns, this is only relevant for checking if the value of
  * `column` is NULL by setting `value` to `null`.
  *
  * For boolean columns, you can also set `value` to `true` or `false` and it
  * will behave the same way as `.eq()`.
  *
  * @param column - The column to filter on
  * @param value - The value to filter with
  *
  * @category Database
  *
  * @exampleDescription Checking for nullness, true or false
  * Using the `eq()` filter doesn't work when filtering for `null`.
  *
  * Instead, you need to use `is()`.
  *
  * @example Checking for nullness, true or false
  * ```ts
  * const { data, error } = await supabase
  *   .from('countries')
  *   .select()
  *   .is('name', null)
  * ```
  *
  * @exampleSql Checking for nullness, true or false
  * ```sql
  * create table
  *   countries (id int8 primary key, name text);
  *
  * insert into
  *   countries (id, name)
  * values
  *   (1, 'null'),
  *   (2, null);
  * ```
  *
  * @exampleResponse Checking for nullness, true or false
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 2,
  *       "name": "null"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  is(column, value) {
    this.url.searchParams.append(column, `is.${value}`);
    return this;
  }
  /**
  * Match only rows where `column` IS DISTINCT FROM `value`.
  *
  * Unlike `.neq()`, this treats `NULL` as a comparable value. Two `NULL` values
  * are considered equal (not distinct), and comparing `NULL` with any non-NULL
  * value returns true (distinct).
  *
  * @param column - The column to filter on
  * @param value - The value to filter with
  */
  isDistinct(column, value) {
    this.url.searchParams.append(column, `isdistinct.${value}`);
    return this;
  }
  /**
  * Match only rows where `column` is included in the `values` array.
  *
  * @param column - The column to filter on
  * @param values - The values array to filter with
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .in('name', ['Leia', 'Han'])
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 2,
  *       "name": "Leia"
  *     },
  *     {
  *       "id": 3,
  *       "name": "Han"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  in(column, values) {
    const cleanedValues = Array.from(new Set(values)).map((s) => {
      if (typeof s === "string" && PostgrestReservedCharsRegexp.test(s)) return `"${s}"`;
      else return `${s}`;
    }).join(",");
    this.url.searchParams.append(column, `in.(${cleanedValues})`);
    return this;
  }
  /**
  * Match only rows where `column` is NOT included in the `values` array.
  *
  * @param column - The column to filter on
  * @param values - The values array to filter with
  */
  notIn(column, values) {
    const cleanedValues = Array.from(new Set(values)).map((s) => {
      if (typeof s === "string" && PostgrestReservedCharsRegexp.test(s)) return `"${s}"`;
      else return `${s}`;
    }).join(",");
    this.url.searchParams.append(column, `not.in.(${cleanedValues})`);
    return this;
  }
  /**
  * Only relevant for jsonb, array, and range columns. Match only rows where
  * `column` contains every element appearing in `value`.
  *
  * @param column - The jsonb, array, or range column to filter on
  * @param value - The jsonb, array, or range value to filter with
  *
  * @category Database
  *
  * @example On array columns
  * ```ts
  * const { data, error } = await supabase
  *   .from('issues')
  *   .select()
  *   .contains('tags', ['is:open', 'priority:low'])
  * ```
  *
  * @exampleSql On array columns
  * ```sql
  * create table
  *   issues (
  *     id int8 primary key,
  *     title text,
  *     tags text[]
  *   );
  *
  * insert into
  *   issues (id, title, tags)
  * values
  *   (1, 'Cache invalidation is not working', array['is:open', 'severity:high', 'priority:low']),
  *   (2, 'Use better names', array['is:open', 'severity:low', 'priority:medium']);
  * ```
  *
  * @exampleResponse On array columns
  * ```json
  * {
  *   "data": [
  *     {
  *       "title": "Cache invalidation is not working"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription On range columns
  * Postgres supports a number of [range
  * types](https://www.postgresql.org/docs/current/rangetypes.html). You
  * can filter on range columns using the string representation of range
  * values.
  *
  * @example On range columns
  * ```ts
  * const { data, error } = await supabase
  *   .from('reservations')
  *   .select()
  *   .contains('during', '[2000-01-01 13:00, 2000-01-01 13:30)')
  * ```
  *
  * @exampleSql On range columns
  * ```sql
  * create table
  *   reservations (
  *     id int8 primary key,
  *     room_name text,
  *     during tsrange
  *   );
  *
  * insert into
  *   reservations (id, room_name, during)
  * values
  *   (1, 'Emerald', '[2000-01-01 13:00, 2000-01-01 15:00)'),
  *   (2, 'Topaz', '[2000-01-02 09:00, 2000-01-02 10:00)');
  * ```
  *
  * @exampleResponse On range columns
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "room_name": "Emerald",
  *       "during": "[\"2000-01-01 13:00:00\",\"2000-01-01 15:00:00\")"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @example On `jsonb` columns
  * ```ts
  * const { data, error } = await supabase
  *   .from('users')
  *   .select('name')
  *   .contains('address', { postcode: 90210 })
  * ```
  *
  * @exampleSql On `jsonb` columns
  * ```sql
  * create table
  *   users (
  *     id int8 primary key,
  *     name text,
  *     address jsonb
  *   );
  *
  * insert into
  *   users (id, name, address)
  * values
  *   (1, 'Michael', '{ "postcode": 90210, "street": "Melrose Place" }'),
  *   (2, 'Jane', '{}');
  * ```
  *
  * @exampleResponse On `jsonb` columns
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "Michael"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  contains(column, value) {
    if (typeof value === "string") this.url.searchParams.append(column, `cs.${value}`);
    else if (Array.isArray(value)) this.url.searchParams.append(column, `cs.{${value.join(",")}}`);
    else this.url.searchParams.append(column, `cs.${JSON.stringify(value)}`);
    return this;
  }
  /**
  * Only relevant for jsonb, array, and range columns. Match only rows where
  * every element appearing in `column` is contained by `value`.
  *
  * @param column - The jsonb, array, or range column to filter on
  * @param value - The jsonb, array, or range value to filter with
  *
  * @category Database
  *
  * @example On array columns
  * ```ts
  * const { data, error } = await supabase
  *   .from('classes')
  *   .select('name')
  *   .containedBy('days', ['monday', 'tuesday', 'wednesday', 'friday'])
  * ```
  *
  * @exampleSql On array columns
  * ```sql
  * create table
  *   classes (
  *     id int8 primary key,
  *     name text,
  *     days text[]
  *   );
  *
  * insert into
  *   classes (id, name, days)
  * values
  *   (1, 'Chemistry', array['monday', 'friday']),
  *   (2, 'History', array['monday', 'wednesday', 'thursday']);
  * ```
  *
  * @exampleResponse On array columns
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "Chemistry"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription On range columns
  * Postgres supports a number of [range
  * types](https://www.postgresql.org/docs/current/rangetypes.html). You
  * can filter on range columns using the string representation of range
  * values.
  *
  * @example On range columns
  * ```ts
  * const { data, error } = await supabase
  *   .from('reservations')
  *   .select()
  *   .containedBy('during', '[2000-01-01 00:00, 2000-01-01 23:59)')
  * ```
  *
  * @exampleSql On range columns
  * ```sql
  * create table
  *   reservations (
  *     id int8 primary key,
  *     room_name text,
  *     during tsrange
  *   );
  *
  * insert into
  *   reservations (id, room_name, during)
  * values
  *   (1, 'Emerald', '[2000-01-01 13:00, 2000-01-01 15:00)'),
  *   (2, 'Topaz', '[2000-01-02 09:00, 2000-01-02 10:00)');
  * ```
  *
  * @exampleResponse On range columns
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "room_name": "Emerald",
  *       "during": "[\"2000-01-01 13:00:00\",\"2000-01-01 15:00:00\")"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @example On `jsonb` columns
  * ```ts
  * const { data, error } = await supabase
  *   .from('users')
  *   .select('name')
  *   .containedBy('address', {})
  * ```
  *
  * @exampleSql On `jsonb` columns
  * ```sql
  * create table
  *   users (
  *     id int8 primary key,
  *     name text,
  *     address jsonb
  *   );
  *
  * insert into
  *   users (id, name, address)
  * values
  *   (1, 'Michael', '{ "postcode": 90210, "street": "Melrose Place" }'),
  *   (2, 'Jane', '{}');
  * ```
  *
  * @exampleResponse On `jsonb` columns
  * ```json
  *   {
  *     "data": [
  *       {
  *         "name": "Jane"
  *       }
  *     ],
  *     "status": 200,
  *     "statusText": "OK"
  *   }
  *
  * ```
  */
  containedBy(column, value) {
    if (typeof value === "string") this.url.searchParams.append(column, `cd.${value}`);
    else if (Array.isArray(value)) this.url.searchParams.append(column, `cd.{${value.join(",")}}`);
    else this.url.searchParams.append(column, `cd.${JSON.stringify(value)}`);
    return this;
  }
  /**
  * Only relevant for range columns. Match only rows where every element in
  * `column` is greater than any element in `range`.
  *
  * @param column - The range column to filter on
  * @param range - The range to filter with
  *
  * @category Database
  *
  * @exampleDescription With `select()`
  * Postgres supports a number of [range
  * types](https://www.postgresql.org/docs/current/rangetypes.html). You
  * can filter on range columns using the string representation of range
  * values.
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('reservations')
  *   .select()
  *   .rangeGt('during', '[2000-01-02 08:00, 2000-01-02 09:00)')
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   reservations (
  *     id int8 primary key,
  *     room_name text,
  *     during tsrange
  *   );
  *
  * insert into
  *   reservations (id, room_name, during)
  * values
  *   (1, 'Emerald', '[2000-01-01 13:00, 2000-01-01 15:00)'),
  *   (2, 'Topaz', '[2000-01-02 09:00, 2000-01-02 10:00)');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  *   {
  *     "data": [
  *       {
  *         "id": 2,
  *         "room_name": "Topaz",
  *         "during": "[\"2000-01-02 09:00:00\",\"2000-01-02 10:00:00\")"
  *       }
  *     ],
  *     "status": 200,
  *     "statusText": "OK"
  *   }
  *
  * ```
  */
  rangeGt(column, range) {
    this.url.searchParams.append(column, `sr.${range}`);
    return this;
  }
  /**
  * Only relevant for range columns. Match only rows where every element in
  * `column` is either contained in `range` or greater than any element in
  * `range`.
  *
  * @param column - The range column to filter on
  * @param range - The range to filter with
  *
  * @category Database
  *
  * @exampleDescription With `select()`
  * Postgres supports a number of [range
  * types](https://www.postgresql.org/docs/current/rangetypes.html). You
  * can filter on range columns using the string representation of range
  * values.
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('reservations')
  *   .select()
  *   .rangeGte('during', '[2000-01-02 08:30, 2000-01-02 09:30)')
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   reservations (
  *     id int8 primary key,
  *     room_name text,
  *     during tsrange
  *   );
  *
  * insert into
  *   reservations (id, room_name, during)
  * values
  *   (1, 'Emerald', '[2000-01-01 13:00, 2000-01-01 15:00)'),
  *   (2, 'Topaz', '[2000-01-02 09:00, 2000-01-02 10:00)');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  *   {
  *     "data": [
  *       {
  *         "id": 2,
  *         "room_name": "Topaz",
  *         "during": "[\"2000-01-02 09:00:00\",\"2000-01-02 10:00:00\")"
  *       }
  *     ],
  *     "status": 200,
  *     "statusText": "OK"
  *   }
  *
  * ```
  */
  rangeGte(column, range) {
    this.url.searchParams.append(column, `nxl.${range}`);
    return this;
  }
  /**
  * Only relevant for range columns. Match only rows where every element in
  * `column` is less than any element in `range`.
  *
  * @param column - The range column to filter on
  * @param range - The range to filter with
  *
  * @category Database
  *
  * @exampleDescription With `select()`
  * Postgres supports a number of [range
  * types](https://www.postgresql.org/docs/current/rangetypes.html). You
  * can filter on range columns using the string representation of range
  * values.
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('reservations')
  *   .select()
  *   .rangeLt('during', '[2000-01-01 15:00, 2000-01-01 16:00)')
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   reservations (
  *     id int8 primary key,
  *     room_name text,
  *     during tsrange
  *   );
  *
  * insert into
  *   reservations (id, room_name, during)
  * values
  *   (1, 'Emerald', '[2000-01-01 13:00, 2000-01-01 15:00)'),
  *   (2, 'Topaz', '[2000-01-02 09:00, 2000-01-02 10:00)');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "room_name": "Emerald",
  *       "during": "[\"2000-01-01 13:00:00\",\"2000-01-01 15:00:00\")"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  rangeLt(column, range) {
    this.url.searchParams.append(column, `sl.${range}`);
    return this;
  }
  /**
  * Only relevant for range columns. Match only rows where every element in
  * `column` is either contained in `range` or less than any element in
  * `range`.
  *
  * @param column - The range column to filter on
  * @param range - The range to filter with
  *
  * @category Database
  *
  * @exampleDescription With `select()`
  * Postgres supports a number of [range
  * types](https://www.postgresql.org/docs/current/rangetypes.html). You
  * can filter on range columns using the string representation of range
  * values.
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('reservations')
  *   .select()
  *   .rangeLte('during', '[2000-01-01 14:00, 2000-01-01 16:00)')
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   reservations (
  *     id int8 primary key,
  *     room_name text,
  *     during tsrange
  *   );
  *
  * insert into
  *   reservations (id, room_name, during)
  * values
  *   (1, 'Emerald', '[2000-01-01 13:00, 2000-01-01 15:00)'),
  *   (2, 'Topaz', '[2000-01-02 09:00, 2000-01-02 10:00)');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  *   {
  *     "data": [
  *       {
  *         "id": 1,
  *         "room_name": "Emerald",
  *         "during": "[\"2000-01-01 13:00:00\",\"2000-01-01 15:00:00\")"
  *       }
  *     ],
  *     "status": 200,
  *     "statusText": "OK"
  *   }
  *
  * ```
  */
  rangeLte(column, range) {
    this.url.searchParams.append(column, `nxr.${range}`);
    return this;
  }
  /**
  * Only relevant for range columns. Match only rows where `column` is
  * mutually exclusive to `range` and there can be no element between the two
  * ranges.
  *
  * @param column - The range column to filter on
  * @param range - The range to filter with
  *
  * @category Database
  *
  * @exampleDescription With `select()`
  * Postgres supports a number of [range
  * types](https://www.postgresql.org/docs/current/rangetypes.html). You
  * can filter on range columns using the string representation of range
  * values.
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('reservations')
  *   .select()
  *   .rangeAdjacent('during', '[2000-01-01 12:00, 2000-01-01 13:00)')
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   reservations (
  *     id int8 primary key,
  *     room_name text,
  *     during tsrange
  *   );
  *
  * insert into
  *   reservations (id, room_name, during)
  * values
  *   (1, 'Emerald', '[2000-01-01 13:00, 2000-01-01 15:00)'),
  *   (2, 'Topaz', '[2000-01-02 09:00, 2000-01-02 10:00)');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "room_name": "Emerald",
  *       "during": "[\"2000-01-01 13:00:00\",\"2000-01-01 15:00:00\")"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  rangeAdjacent(column, range) {
    this.url.searchParams.append(column, `adj.${range}`);
    return this;
  }
  /**
  * Only relevant for array and range columns. Match only rows where
  * `column` and `value` have an element in common.
  *
  * @param column - The array or range column to filter on
  * @param value - The array or range value to filter with
  *
  * @category Database
  *
  * @example On array columns
  * ```ts
  * const { data, error } = await supabase
  *   .from('issues')
  *   .select('title')
  *   .overlaps('tags', ['is:closed', 'severity:high'])
  * ```
  *
  * @exampleSql On array columns
  * ```sql
  * create table
  *   issues (
  *     id int8 primary key,
  *     title text,
  *     tags text[]
  *   );
  *
  * insert into
  *   issues (id, title, tags)
  * values
  *   (1, 'Cache invalidation is not working', array['is:open', 'severity:high', 'priority:low']),
  *   (2, 'Use better names', array['is:open', 'severity:low', 'priority:medium']);
  * ```
  *
  * @exampleResponse On array columns
  * ```json
  * {
  *   "data": [
  *     {
  *       "title": "Cache invalidation is not working"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription On range columns
  * Postgres supports a number of [range
  * types](https://www.postgresql.org/docs/current/rangetypes.html). You
  * can filter on range columns using the string representation of range
  * values.
  *
  * @example On range columns
  * ```ts
  * const { data, error } = await supabase
  *   .from('reservations')
  *   .select()
  *   .overlaps('during', '[2000-01-01 12:45, 2000-01-01 13:15)')
  * ```
  *
  * @exampleSql On range columns
  * ```sql
  * create table
  *   reservations (
  *     id int8 primary key,
  *     room_name text,
  *     during tsrange
  *   );
  *
  * insert into
  *   reservations (id, room_name, during)
  * values
  *   (1, 'Emerald', '[2000-01-01 13:00, 2000-01-01 15:00)'),
  *   (2, 'Topaz', '[2000-01-02 09:00, 2000-01-02 10:00)');
  * ```
  *
  * @exampleResponse On range columns
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "room_name": "Emerald",
  *       "during": "[\"2000-01-01 13:00:00\",\"2000-01-01 15:00:00\")"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  overlaps(column, value) {
    if (typeof value === "string") this.url.searchParams.append(column, `ov.${value}`);
    else this.url.searchParams.append(column, `ov.{${value.join(",")}}`);
    return this;
  }
  /**
  * Only relevant for text and tsvector columns. Match only rows where
  * `column` matches the query string in `query`.
  *
  * @param column - The text or tsvector column to filter on
  * @param query - The query text to match with
  * @param options - Named parameters
  * @param options.config - The text search configuration to use
  * @param options.type - Change how the `query` text is interpreted
  *
  * @category Database
  *
  * @remarks
  * - For more information, see [Postgres full text search](/docs/guides/database/full-text-search).
  *
  * @example Text search
  * ```ts
  * const result = await supabase
  *   .from("texts")
  *   .select("content")
  *   .textSearch("content", `'eggs' & 'ham'`, {
  *     config: "english",
  *   });
  * ```
  *
  * @exampleSql Text search
  * ```sql
  * create table texts (
  *   id      bigint
  *           primary key
  *           generated always as identity,
  *   content text
  * );
  *
  * insert into texts (content) values
  *     ('Four score and seven years ago'),
  *     ('The road goes ever on and on'),
  *     ('Green eggs and ham')
  * ;
  * ```
  *
  * @exampleResponse Text search
  * ```json
  * {
  *   "data": [
  *     {
  *       "content": "Green eggs and ham"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription Basic normalization
  * Uses PostgreSQL's `plainto_tsquery` function.
  *
  * @example Basic normalization
  * ```ts
  * const { data, error } = await supabase
  *   .from('quotes')
  *   .select('catchphrase')
  *   .textSearch('catchphrase', `'fat' & 'cat'`, {
  *     type: 'plain',
  *     config: 'english'
  *   })
  * ```
  *
  * @exampleDescription Full normalization
  * Uses PostgreSQL's `phraseto_tsquery` function.
  *
  * @example Full normalization
  * ```ts
  * const { data, error } = await supabase
  *   .from('quotes')
  *   .select('catchphrase')
  *   .textSearch('catchphrase', `'fat' & 'cat'`, {
  *     type: 'phrase',
  *     config: 'english'
  *   })
  * ```
  *
  * @exampleDescription Websearch
  * Uses PostgreSQL's `websearch_to_tsquery` function.
  * This function will never raise syntax errors, which makes it possible to use raw user-supplied input for search, and can be used
  * with advanced operators.
  *
  * - `unquoted text`: text not inside quote marks will be converted to terms separated by & operators, as if processed by plainto_tsquery.
  * - `"quoted text"`: text inside quote marks will be converted to terms separated by `<->` operators, as if processed by phraseto_tsquery.
  * - `OR`: the word “or” will be converted to the | operator.
  * - `-`: a dash will be converted to the ! operator.
  *
  * @example Websearch
  * ```ts
  * const { data, error } = await supabase
  *   .from('quotes')
  *   .select('catchphrase')
  *   .textSearch('catchphrase', `'fat or cat'`, {
  *     type: 'websearch',
  *     config: 'english'
  *   })
  * ```
  */
  textSearch(column, query, { config, type } = {}) {
    let typePart = "";
    if (type === "plain") typePart = "pl";
    else if (type === "phrase") typePart = "ph";
    else if (type === "websearch") typePart = "w";
    const configPart = config === void 0 ? "" : `(${config})`;
    this.url.searchParams.append(column, `${typePart}fts${configPart}.${query}`);
    return this;
  }
  /**
  * Match only rows where each column in `query` keys is equal to its
  * associated value. Shorthand for multiple `.eq()`s.
  *
  * @param query - The object to filter with, with column names as keys mapped
  * to their filter values
  *
  * @category Database
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select('name')
  *   .match({ id: 2, name: 'Leia' })
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "Leia"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  match(query) {
    Object.entries(query).filter(([_, value]) => value !== void 0).forEach(([column, value]) => {
      this.url.searchParams.append(column, `eq.${value}`);
    });
    return this;
  }
  /**
  * Match only rows which doesn't satisfy the filter.
  *
  * Unlike most filters, `opearator` and `value` are used as-is and need to
  * follow [PostgREST
  * syntax](https://postgrest.org/en/stable/api.html#operators). You also need
  * to make sure they are properly sanitized.
  *
  * @param column - The column to filter on
  * @param operator - The operator to be negated to filter with, following
  * PostgREST syntax
  * @param value - The value to filter with, following PostgREST syntax
  *
  * @category Database
  *
  * @remarks
  * not() expects you to use the raw PostgREST syntax for the filter values.
  *
  * ```ts
  * .not('id', 'in', '(5,6,7)')  // Use `()` for `in` filter
  * .not('arraycol', 'cs', '{"a","b"}')  // Use `cs` for `contains()`, `{}` for array values
  * ```
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('countries')
  *   .select()
  *   .not('name', 'is', null)
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   countries (id int8 primary key, name text);
  *
  * insert into
  *   countries (id, name)
  * values
  *   (1, 'null'),
  *   (2, null);
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  *   {
  *     "data": [
  *       {
  *         "id": 1,
  *         "name": "null"
  *       }
  *     ],
  *     "status": 200,
  *     "statusText": "OK"
  *   }
  *
  * ```
  */
  not(column, operator, value) {
    this.url.searchParams.append(column, `not.${operator}.${value}`);
    return this;
  }
  /**
  * Match only rows which satisfy at least one of the filters.
  *
  * Unlike most filters, `filters` is used as-is and needs to follow [PostgREST
  * syntax](https://postgrest.org/en/stable/api.html#operators). You also need
  * to make sure it's properly sanitized.
  *
  * It's currently not possible to do an `.or()` filter across multiple tables.
  *
  * @param filters - The filters to use, following PostgREST syntax
  * @param options - Named parameters
  * @param options.referencedTable - Set this to filter on referenced tables
  * instead of the parent table
  * @param options.foreignTable - Deprecated, use `referencedTable` instead
  *
  * @category Database
  *
  * @remarks
  * or() expects you to use the raw PostgREST syntax for the filter names and values.
  *
  * ```ts
  * .or('id.in.(5,6,7), arraycol.cs.{"a","b"}')  // Use `()` for `in` filter, `{}` for array values and `cs` for `contains()`.
  * .or('id.in.(5,6,7), arraycol.cd.{"a","b"}')  // Use `cd` for `containedBy()`
  * ```
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select('name')
  *   .or('id.eq.2,name.eq.Han')
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "Leia"
  *     },
  *     {
  *       "name": "Han"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @example Use `or` with `and`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select('name')
  *   .or('id.gt.3,and(id.eq.1,name.eq.Luke)')
  * ```
  *
  * @exampleSql Use `or` with `and`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse Use `or` with `and`
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "Luke"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @example Use `or` on referenced tables
  * ```ts
  * const { data, error } = await supabase
  *   .from('orchestral_sections')
  *   .select(`
  *     name,
  *     instruments!inner (
  *       name
  *     )
  *   `)
  *   .or('section_id.eq.1,name.eq.guzheng', { referencedTable: 'instruments' })
  * ```
  *
  * @exampleSql Use `or` on referenced tables
  * ```sql
  * create table
  *   orchestral_sections (id int8 primary key, name text);
  * create table
  *   instruments (
  *     id int8 primary key,
  *     section_id int8 not null references orchestral_sections,
  *     name text
  *   );
  *
  * insert into
  *   orchestral_sections (id, name)
  * values
  *   (1, 'strings'),
  *   (2, 'woodwinds');
  * insert into
  *   instruments (id, section_id, name)
  * values
  *   (1, 2, 'flute'),
  *   (2, 1, 'violin');
  * ```
  *
  * @exampleResponse Use `or` on referenced tables
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "strings",
  *       "instruments": [
  *         {
  *           "name": "violin"
  *         }
  *       ]
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  or(filters, { foreignTable, referencedTable = foreignTable } = {}) {
    const key = referencedTable ? `${referencedTable}.or` : "or";
    this.url.searchParams.append(key, `(${filters})`);
    return this;
  }
  /**
  * Match only rows which satisfy the filter. This is an escape hatch - you
  * should use the specific filter methods wherever possible.
  *
  * Unlike most filters, `opearator` and `value` are used as-is and need to
  * follow [PostgREST
  * syntax](https://postgrest.org/en/stable/api.html#operators). You also need
  * to make sure they are properly sanitized.
  *
  * @param column - The column to filter on
  * @param operator - The operator to filter with, following PostgREST syntax
  * @param value - The value to filter with, following PostgREST syntax
  *
  * @category Database
  *
  * @remarks
  * filter() expects you to use the raw PostgREST syntax for the filter values.
  *
  * ```ts
  * .filter('id', 'in', '(5,6,7)')  // Use `()` for `in` filter
  * .filter('arraycol', 'cs', '{"a","b"}')  // Use `cs` for `contains()`, `{}` for array values
  * ```
  *
  * @example With `select()`
  * ```ts
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  *   .filter('name', 'in', '("Han","Yoda")')
  * ```
  *
  * @exampleSql With `select()`
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse With `select()`
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 3,
  *       "name": "Han"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @example On a referenced table
  * ```ts
  * const { data, error } = await supabase
  *   .from('orchestral_sections')
  *   .select(`
  *     name,
  *     instruments!inner (
  *       name
  *     )
  *   `)
  *   .filter('instruments.name', 'eq', 'flute')
  * ```
  *
  * @exampleSql On a referenced table
  * ```sql
  * create table
  *   orchestral_sections (id int8 primary key, name text);
  * create table
  *    instruments (
  *     id int8 primary key,
  *     section_id int8 not null references orchestral_sections,
  *     name text
  *   );
  *
  * insert into
  *   orchestral_sections (id, name)
  * values
  *   (1, 'strings'),
  *   (2, 'woodwinds');
  * insert into
  *   instruments (id, section_id, name)
  * values
  *   (1, 2, 'flute'),
  *   (2, 1, 'violin');
  * ```
  *
  * @exampleResponse On a referenced table
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "woodwinds",
  *       "instruments": [
  *         {
  *           "name": "flute"
  *         }
  *       ]
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  filter(column, operator, value) {
    this.url.searchParams.append(column, `${operator}.${value}`);
    return this;
  }
};
var PostgrestQueryBuilder = class {
  /**
  * Creates a query builder scoped to a Postgres table or view.
  *
  * @category Database
  *
  * @param url - The URL for the query
  * @param options - Named parameters
  * @param options.headers - Custom headers
  * @param options.schema - Postgres schema to use
  * @param options.fetch - Custom fetch implementation
  * @param options.urlLengthLimit - Maximum URL length before warning
  * @param options.retry - Enable automatic retries for transient errors (default: true)
  *
  * @example Using supabase-js (recommended)
  * ```ts
  * import { createClient } from '@supabase/supabase-js'
  *
  * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key')
  * const { data, error } = await supabase.from('users').select('*')
  * ```
  *
  * @example Standalone import for bundle-sensitive environments
  * ```ts
  * import { PostgrestQueryBuilder } from '@supabase/postgrest-js'
  *
  * const query = new PostgrestQueryBuilder(
  *   new URL('https://xyzcompany.supabase.co/rest/v1/users'),
  *   { headers: { apikey: 'publishable-or-anon-key' }, retry: true }
  * )
  * ```
  */
  constructor(url, { headers = {}, schema, fetch: fetch$1, urlLengthLimit = 8e3, retry }) {
    this.url = url;
    this.headers = new Headers(headers);
    this.schema = schema;
    this.fetch = fetch$1;
    this.urlLengthLimit = urlLengthLimit;
    this.retry = retry;
  }
  /**
  * Clone URL and headers to prevent shared state between operations.
  */
  cloneRequestState() {
    return {
      url: new URL(this.url.toString()),
      headers: new Headers(this.headers)
    };
  }
  /**
  * Perform a SELECT query on the table or view.
  *
  * @param columns - The columns to retrieve, separated by commas. Columns can be renamed when returned with `customName:columnName`
  *
  * @param options - Named parameters
  *
  * @param options.head - When set to `true`, `data` will not be returned.
  * Useful if you only need the count.
  *
  * @param options.count - Count algorithm to use to count rows in the table or view.
  *
  * `"exact"`: Exact but slow count algorithm. Performs a `COUNT(*)` under the
  * hood.
  *
  * `"planned"`: Approximated but fast count algorithm. Uses the Postgres
  * statistics under the hood.
  *
  * `"estimated"`: Uses exact count for low numbers and planned count for high
  * numbers.
  *
  * @remarks
  * When using `count` with `.range()` or `.limit()`, the returned `count` is the total number of rows
  * that match your filters, not the number of rows in the current page. Use this to build pagination UI.
  
  * - By default, Supabase projects return a maximum of 1,000 rows. This setting can be changed in your project's [API settings](/dashboard/project/_/settings/api). It's recommended that you keep it low to limit the payload size of accidental or malicious requests. You can use `range()` queries to paginate through your data.
  * - `select()` can be combined with [Filters](/docs/reference/javascript/using-filters)
  * - `select()` can be combined with [Modifiers](/docs/reference/javascript/using-modifiers)
  * - `apikey` is a reserved keyword if you're using the [Supabase Platform](/docs/guides/platform) and [should be avoided as a column name](https://github.com/supabase/supabase/issues/5465). *
  * @category Database
  *
  * @example Getting your data
  * ```js
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select()
  * ```
  *
  * @exampleSql Getting your data
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Harry'),
  *   (2, 'Frodo'),
  *   (3, 'Katniss');
  * ```
  *
  * @exampleResponse Getting your data
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "Harry"
  *     },
  *     {
  *       "id": 2,
  *       "name": "Frodo"
  *     },
  *     {
  *       "id": 3,
  *       "name": "Katniss"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @example Selecting specific columns
  * ```js
  * const { data, error } = await supabase
  *   .from('characters')
  *   .select('name')
  * ```
  *
  * @exampleSql Selecting specific columns
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Frodo'),
  *   (2, 'Harry'),
  *   (3, 'Katniss');
  * ```
  *
  * @exampleResponse Selecting specific columns
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "Frodo"
  *     },
  *     {
  *       "name": "Harry"
  *     },
  *     {
  *       "name": "Katniss"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription Query referenced tables
  * If your database has foreign key relationships, you can query related tables too.
  *
  * @example Query referenced tables
  * ```js
  * const { data, error } = await supabase
  *   .from('orchestral_sections')
  *   .select(`
  *     name,
  *     instruments (
  *       name
  *     )
  *   `)
  * ```
  *
  * @exampleSql Query referenced tables
  * ```sql
  * create table
  *   orchestral_sections (id int8 primary key, name text);
  * create table
  *   instruments (
  *     id int8 primary key,
  *     section_id int8 not null references orchestral_sections,
  *     name text
  *   );
  *
  * insert into
  *   orchestral_sections (id, name)
  * values
  *   (1, 'strings'),
  *   (2, 'woodwinds');
  * insert into
  *   instruments (id, section_id, name)
  * values
  *   (1, 2, 'flute'),
  *   (2, 1, 'violin');
  * ```
  *
  * @exampleResponse Query referenced tables
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "strings",
  *       "instruments": [
  *         {
  *           "name": "violin"
  *         }
  *       ]
  *     },
  *     {
  *       "name": "woodwinds",
  *       "instruments": [
  *         {
  *           "name": "flute"
  *         }
  *       ]
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription Query referenced tables with spaces in their names
  * If your table name contains spaces, you must use double quotes in the `select` statement to reference the table.
  *
  * @example Query referenced tables with spaces in their names
  * ```js
  * const { data, error } = await supabase
  *   .from('orchestral sections')
  *   .select(`
  *     name,
  *     "musical instruments" (
  *       name
  *     )
  *   `)
  * ```
  *
  * @exampleSql Query referenced tables with spaces in their names
  * ```sql
  * create table
  *   "orchestral sections" (id int8 primary key, name text);
  * create table
  *   "musical instruments" (
  *     id int8 primary key,
  *     section_id int8 not null references "orchestral sections",
  *     name text
  *   );
  *
  * insert into
  *   "orchestral sections" (id, name)
  * values
  *   (1, 'strings'),
  *   (2, 'woodwinds');
  * insert into
  *   "musical instruments" (id, section_id, name)
  * values
  *   (1, 2, 'flute'),
  *   (2, 1, 'violin');
  * ```
  *
  * @exampleResponse Query referenced tables with spaces in their names
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "strings",
  *       "musical instruments": [
  *         {
  *           "name": "violin"
  *         }
  *       ]
  *     },
  *     {
  *       "name": "woodwinds",
  *       "musical instruments": [
  *         {
  *           "name": "flute"
  *         }
  *       ]
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription Query referenced tables through a join table
  * If you're in a situation where your tables are **NOT** directly
  * related, but instead are joined by a _join table_, you can still use
  * the `select()` method to query the related data. The join table needs
  * to have the foreign keys as part of its composite primary key.
  *
  * @example Query referenced tables through a join table
  * ```ts
  * const { data, error } = await supabase
  *   .from('users')
  *   .select(`
  *     name,
  *     teams (
  *       name
  *     )
  *   `)
  *   
  * ```
  *
  * @exampleSql Query referenced tables through a join table
  * ```sql
  * create table
  *   users (
  *     id int8 primary key,
  *     name text
  *   );
  * create table
  *   teams (
  *     id int8 primary key,
  *     name text
  *   );
  * -- join table
  * create table
  *   users_teams (
  *     user_id int8 not null references users,
  *     team_id int8 not null references teams,
  *     -- both foreign keys must be part of a composite primary key
  *     primary key (user_id, team_id)
  *   );
  *
  * insert into
  *   users (id, name)
  * values
  *   (1, 'Kiran'),
  *   (2, 'Evan');
  * insert into
  *   teams (id, name)
  * values
  *   (1, 'Green'),
  *   (2, 'Blue');
  * insert into
  *   users_teams (user_id, team_id)
  * values
  *   (1, 1),
  *   (1, 2),
  *   (2, 2);
  * ```
  *
  * @exampleResponse Query referenced tables through a join table
  * ```json
  *   {
  *     "data": [
  *       {
  *         "name": "Kiran",
  *         "teams": [
  *           {
  *             "name": "Green"
  *           },
  *           {
  *             "name": "Blue"
  *           }
  *         ]
  *       },
  *       {
  *         "name": "Evan",
  *         "teams": [
  *           {
  *             "name": "Blue"
  *           }
  *         ]
  *       }
  *     ],
  *     "status": 200,
  *     "statusText": "OK"
  *   }
  *   
  * ```
  *
  * @exampleDescription Query the same referenced table multiple times
  * If you need to query the same referenced table twice, use the name of the
  * joined column to identify which join to use. You can also give each
  * column an alias.
  *
  * @example Query the same referenced table multiple times
  * ```ts
  * const { data, error } = await supabase
  *   .from('messages')
  *   .select(`
  *     content,
  *     from:sender_id(name),
  *     to:receiver_id(name)
  *   `)
  *
  * // To infer types, use the name of the table (in this case `users`) and
  * // the name of the foreign key constraint.
  * const { data, error } = await supabase
  *   .from('messages')
  *   .select(`
  *     content,
  *     from:users!messages_sender_id_fkey(name),
  *     to:users!messages_receiver_id_fkey(name)
  *   `)
  * ```
  *
  * @exampleSql Query the same referenced table multiple times
  * ```sql
  *  create table
  *  users (id int8 primary key, name text);
  *
  *  create table
  *    messages (
  *      sender_id int8 not null references users,
  *      receiver_id int8 not null references users,
  *      content text
  *    );
  *
  *  insert into
  *    users (id, name)
  *  values
  *    (1, 'Kiran'),
  *    (2, 'Evan');
  *
  *  insert into
  *    messages (sender_id, receiver_id, content)
  *  values
  *    (1, 2, '👋');
  *  ```
  * ```
  *
  * @exampleResponse Query the same referenced table multiple times
  * ```json
  * {
  *   "data": [
  *     {
  *       "content": "👋",
  *       "from": {
  *         "name": "Kiran"
  *       },
  *       "to": {
  *         "name": "Evan"
  *       }
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription Query nested foreign tables through a join table
  * You can use the result of a joined table to gather data in
  * another foreign table. With multiple references to the same foreign
  * table you must specify the column on which to conduct the join.
  *
  * @example Query nested foreign tables through a join table
  * ```ts
  *   const { data, error } = await supabase
  *     .from('games')
  *     .select(`
  *       game_id:id,
  *       away_team:teams!games_away_team_fkey (
  *         users (
  *           id,
  *           name
  *         )
  *       )
  *     `)
  *   
  * ```
  *
  * @exampleSql Query nested foreign tables through a join table
  * ```sql
  * ```sql
  * create table
  *   users (
  *     id int8 primary key,
  *     name text
  *   );
  * create table
  *   teams (
  *     id int8 primary key,
  *     name text
  *   );
  * -- join table
  * create table
  *   users_teams (
  *     user_id int8 not null references users,
  *     team_id int8 not null references teams,
  *
  *     primary key (user_id, team_id)
  *   );
  * create table
  *   games (
  *     id int8 primary key,
  *     home_team int8 not null references teams,
  *     away_team int8 not null references teams,
  *     name text
  *   );
  *
  * insert into users (id, name)
  * values
  *   (1, 'Kiran'),
  *   (2, 'Evan');
  * insert into
  *   teams (id, name)
  * values
  *   (1, 'Green'),
  *   (2, 'Blue');
  * insert into
  *   users_teams (user_id, team_id)
  * values
  *   (1, 1),
  *   (1, 2),
  *   (2, 2);
  * insert into
  *   games (id, home_team, away_team, name)
  * values
  *   (1, 1, 2, 'Green vs Blue'),
  *   (2, 2, 1, 'Blue vs Green');
  * ```
  *
  * @exampleResponse Query nested foreign tables through a join table
  * ```json
  *   {
  *     "data": [
  *       {
  *         "game_id": 1,
  *         "away_team": {
  *           "users": [
  *             {
  *               "id": 1,
  *               "name": "Kiran"
  *             },
  *             {
  *               "id": 2,
  *               "name": "Evan"
  *             }
  *           ]
  *         }
  *       },
  *       {
  *         "game_id": 2,
  *         "away_team": {
  *           "users": [
  *             {
  *               "id": 1,
  *               "name": "Kiran"
  *             }
  *           ]
  *         }
  *       }
  *     ],
  *     "status": 200,
  *     "statusText": "OK"
  *   }
  *   
  * ```
  *
  * @exampleDescription Filtering through referenced tables
  * If the filter on a referenced table's column is not satisfied, the referenced
  * table returns `[]` or `null` but the parent table is not filtered out.
  * If you want to filter out the parent table rows, use the `!inner` hint
  *
  * @example Filtering through referenced tables
  * ```ts
  * const { data, error } = await supabase
  *   .from('instruments')
  *   .select('name, orchestral_sections(*)')
  *   .eq('orchestral_sections.name', 'percussion')
  * ```
  *
  * @exampleSql Filtering through referenced tables
  * ```sql
  * create table
  *   orchestral_sections (id int8 primary key, name text);
  * create table
  *   instruments (
  *     id int8 primary key,
  *     section_id int8 not null references orchestral_sections,
  *     name text
  *   );
  *
  * insert into
  *   orchestral_sections (id, name)
  * values
  *   (1, 'strings'),
  *   (2, 'woodwinds');
  * insert into
  *   instruments (id, section_id, name)
  * values
  *   (1, 2, 'flute'),
  *   (2, 1, 'violin');
  * ```
  *
  * @exampleResponse Filtering through referenced tables
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "flute",
  *       "orchestral_sections": null
  *     },
  *     {
  *       "name": "violin",
  *       "orchestral_sections": null
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription Querying referenced table with count
  * You can get the number of rows in a related table by using the
  * **count** property.
  *
  * @example Querying referenced table with count
  * ```ts
  * const { data, error } = await supabase
  *   .from('orchestral_sections')
  *   .select(`*, instruments(count)`)
  * ```
  *
  * @exampleSql Querying referenced table with count
  * ```sql
  * create table orchestral_sections (
  *   "id" "uuid" primary key default "extensions"."uuid_generate_v4"() not null,
  *   "name" text
  * );
  *
  * create table characters (
  *   "id" "uuid" primary key default "extensions"."uuid_generate_v4"() not null,
  *   "name" text,
  *   "section_id" "uuid" references public.orchestral_sections on delete cascade
  * );
  *
  * with section as (
  *   insert into orchestral_sections (name)
  *   values ('strings') returning id
  * )
  * insert into instruments (name, section_id) values
  * ('violin', (select id from section)),
  * ('viola', (select id from section)),
  * ('cello', (select id from section)),
  * ('double bass', (select id from section));
  * ```
  *
  * @exampleResponse Querying referenced table with count
  * ```json
  * [
  *   {
  *     "id": "693694e7-d993-4360-a6d7-6294e325d9b6",
  *     "name": "strings",
  *     "instruments": [
  *       {
  *         "count": 4
  *       }
  *     ]
  *   }
  * ]
  * ```
  *
  * @exampleDescription Querying with count option
  * You can get the number of rows by using the
  * [count](/docs/reference/javascript/select#parameters) option.
  *
  * @example Querying with count option
  * ```ts
  * const { count, error } = await supabase
  *   .from('characters')
  *   .select('*', { count: 'exact', head: true })
  * ```
  *
  * @exampleSql Querying with count option
  * ```sql
  * create table
  *   characters (id int8 primary key, name text);
  *
  * insert into
  *   characters (id, name)
  * values
  *   (1, 'Luke'),
  *   (2, 'Leia'),
  *   (3, 'Han');
  * ```
  *
  * @exampleResponse Querying with count option
  * ```json
  * {
  *   "count": 3,
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription Querying JSON data
  * You can select and filter data inside of
  * [JSON](/docs/guides/database/json) columns. Postgres offers some
  * [operators](/docs/guides/database/json#query-the-jsonb-data) for
  * querying JSON data.
  *
  * @example Querying JSON data
  * ```ts
  * const { data, error } = await supabase
  *   .from('users')
  *   .select(`
  *     id, name,
  *     address->city
  *   `)
  * ```
  *
  * @exampleSql Querying JSON data
  * ```sql
  * create table
  *   users (
  *     id int8 primary key,
  *     name text,
  *     address jsonb
  *   );
  *
  * insert into
  *   users (id, name, address)
  * values
  *   (1, 'Frodo', '{"city":"Hobbiton"}');
  * ```
  *
  * @exampleResponse Querying JSON data
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "Frodo",
  *       "city": "Hobbiton"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription Querying referenced table with inner join
  * If you don't want to return the referenced table contents, you can leave the parenthesis empty.
  * Like `.select('name, orchestral_sections!inner()')`.
  *
  * @example Querying referenced table with inner join
  * ```ts
  * const { data, error } = await supabase
  *   .from('instruments')
  *   .select('name, orchestral_sections!inner(name)')
  *   .eq('orchestral_sections.name', 'woodwinds')
  *   .limit(1)
  * ```
  *
  * @exampleSql Querying referenced table with inner join
  * ```sql
  * create table orchestral_sections (
  *   "id" "uuid" primary key default "extensions"."uuid_generate_v4"() not null,
  *   "name" text
  * );
  *
  * create table instruments (
  *   "id" "uuid" primary key default "extensions"."uuid_generate_v4"() not null,
  *   "name" text,
  *   "section_id" "uuid" references public.orchestral_sections on delete cascade
  * );
  *
  * with section as (
  *   insert into orchestral_sections (name)
  *   values ('woodwinds') returning id
  * )
  * insert into instruments (name, section_id) values
  * ('flute', (select id from section)),
  * ('clarinet', (select id from section)),
  * ('bassoon', (select id from section)),
  * ('piccolo', (select id from section));
  * ```
  *
  * @exampleResponse Querying referenced table with inner join
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "flute",
  *       "orchestral_sections": {"name": "woodwinds"}
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription Switching schemas per query
  * In addition to setting the schema during initialization, you can also switch schemas on a per-query basis.
  * Make sure you've set up your [database privileges and API settings](/docs/guides/api/using-custom-schemas).
  *
  * @example Switching schemas per query
  * ```ts
  * const { data, error } = await supabase
  *   .schema('myschema')
  *   .from('mytable')
  *   .select()
  * ```
  *
  * @exampleSql Switching schemas per query
  * ```sql
  * create schema myschema;
  *
  * create table myschema.mytable (
  *   id uuid primary key default gen_random_uuid(),
  *   data text
  * );
  *
  * insert into myschema.mytable (data) values ('mydata');
  * ```
  *
  * @exampleResponse Switching schemas per query
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": "4162e008-27b0-4c0f-82dc-ccaeee9a624d",
  *       "data": "mydata"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  select(columns, options) {
    const { head: head2 = false, count } = options !== null && options !== void 0 ? options : {};
    const method = head2 ? "HEAD" : "GET";
    let quoted = false;
    const cleanedColumns = (columns !== null && columns !== void 0 ? columns : "*").split("").map((c) => {
      if (/\s/.test(c) && !quoted) return "";
      if (c === '"') quoted = !quoted;
      return c;
    }).join("");
    const { url, headers } = this.cloneRequestState();
    url.searchParams.set("select", cleanedColumns);
    if (count) headers.append("Prefer", `count=${count}`);
    return new PostgrestFilterBuilder({
      method,
      url,
      headers,
      schema: this.schema,
      fetch: this.fetch,
      urlLengthLimit: this.urlLengthLimit,
      retry: this.retry
    });
  }
  /**
  * Perform an INSERT into the table or view.
  *
  * By default, inserted rows are not returned. To return it, chain the call
  * with `.select()`.
  *
  * @param values - The values to insert. Pass an object to insert a single row
  * or an array to insert multiple rows.
  *
  * @param options - Named parameters
  *
  * @param options.count - Count algorithm to use to count inserted rows.
  *
  * `"exact"`: Exact but slow count algorithm. Performs a `COUNT(*)` under the
  * hood.
  *
  * `"planned"`: Approximated but fast count algorithm. Uses the Postgres
  * statistics under the hood.
  *
  * `"estimated"`: Uses exact count for low numbers and planned count for high
  * numbers.
  *
  * @param options.defaultToNull - Make missing fields default to `null`.
  * Otherwise, use the default value for the column. Only applies for bulk
  * inserts.
  *
  * @category Database
  *
  * @example Create a record
  * ```ts
  * const { error } = await supabase
  *   .from('countries')
  *   .insert({ id: 1, name: 'Mordor' })
  * ```
  *
  * @exampleSql Create a record
  * ```sql
  * create table
  *   countries (id int8 primary key, name text);
  * ```
  *
  * @exampleResponse Create a record
  * ```json
  * {
  *   "status": 201,
  *   "statusText": "Created"
  * }
  * ```
  *
  * @example Create a record and return it
  * ```ts
  * const { data, error } = await supabase
  *   .from('countries')
  *   .insert({ id: 1, name: 'Mordor' })
  *   .select()
  * ```
  *
  * @exampleSql Create a record and return it
  * ```sql
  * create table
  *   countries (id int8 primary key, name text);
  * ```
  *
  * @exampleResponse Create a record and return it
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "Mordor"
  *     }
  *   ],
  *   "status": 201,
  *   "statusText": "Created"
  * }
  * ```
  *
  * @exampleDescription Bulk create
  * A bulk create operation is handled in a single transaction.
  * If any of the inserts fail, none of the rows are inserted.
  *
  * @example Bulk create
  * ```ts
  * const { error } = await supabase
  *   .from('countries')
  *   .insert([
  *     { id: 1, name: 'Mordor' },
  *     { id: 1, name: 'The Shire' },
  *   ])
  * ```
  *
  * @exampleSql Bulk create
  * ```sql
  * create table
  *   countries (id int8 primary key, name text);
  * ```
  *
  * @exampleResponse Bulk create
  * ```json
  * {
  *   "error": {
  *     "code": "23505",
  *     "details": "Key (id)=(1) already exists.",
  *     "hint": null,
  *     "message": "duplicate key value violates unique constraint \"countries_pkey\""
  *   },
  *   "status": 409,
  *   "statusText": "Conflict"
  * }
  * ```
  */
  insert(values, { count, defaultToNull = true } = {}) {
    var _this$fetch;
    const method = "POST";
    const { url, headers } = this.cloneRequestState();
    if (count) headers.append("Prefer", `count=${count}`);
    if (!defaultToNull) headers.append("Prefer", `missing=default`);
    if (Array.isArray(values)) {
      const columns = values.reduce((acc, x) => acc.concat(Object.keys(x)), []);
      if (columns.length > 0) {
        const uniqueColumns = [...new Set(columns)].map((column) => `"${column}"`);
        url.searchParams.set("columns", uniqueColumns.join(","));
      }
    }
    return new PostgrestFilterBuilder({
      method,
      url,
      headers,
      schema: this.schema,
      body: values,
      fetch: (_this$fetch = this.fetch) !== null && _this$fetch !== void 0 ? _this$fetch : fetch,
      urlLengthLimit: this.urlLengthLimit,
      retry: this.retry
    });
  }
  /**
  * Perform an UPSERT on the table or view. Depending on the column(s) passed
  * to `onConflict`, `.upsert()` allows you to perform the equivalent of
  * `.insert()` if a row with the corresponding `onConflict` columns doesn't
  * exist, or if it does exist, perform an alternative action depending on
  * `ignoreDuplicates`.
  *
  * By default, upserted rows are not returned. To return it, chain the call
  * with `.select()`.
  *
  * @param values - The values to upsert with. Pass an object to upsert a
  * single row or an array to upsert multiple rows.
  *
  * @param options - Named parameters
  *
  * @param options.onConflict - Comma-separated UNIQUE column(s) to specify how
  * duplicate rows are determined. Two rows are duplicates if all the
  * `onConflict` columns are equal.
  *
  * @param options.ignoreDuplicates - If `true`, duplicate rows are ignored. If
  * `false`, duplicate rows are merged with existing rows.
  *
  * @param options.count - Count algorithm to use to count upserted rows.
  *
  * `"exact"`: Exact but slow count algorithm. Performs a `COUNT(*)` under the
  * hood.
  *
  * `"planned"`: Approximated but fast count algorithm. Uses the Postgres
  * statistics under the hood.
  *
  * `"estimated"`: Uses exact count for low numbers and planned count for high
  * numbers.
  *
  * @param options.defaultToNull - Make missing fields default to `null`.
  * Otherwise, use the default value for the column. This only applies when
  * inserting new rows, not when merging with existing rows under
  * `ignoreDuplicates: false`. This also only applies when doing bulk upserts.
  *
  * @example Upsert a single row using a unique key
  * ```ts
  * // Upserting a single row, overwriting based on the 'username' unique column
  * const { data, error } = await supabase
  *   .from('users')
  *   .upsert({ username: 'supabot' }, { onConflict: 'username' })
  *
  * // Example response:
  * // {
  * //   data: [
  * //     { id: 4, message: 'bar', username: 'supabot' }
  * //   ],
  * //   error: null
  * // }
  * ```
  *
  * @example Upsert with conflict resolution and exact row counting
  * ```ts
  * // Upserting and returning exact count
  * const { data, error, count } = await supabase
  *   .from('users')
  *   .upsert(
  *     {
  *       id: 3,
  *       message: 'foo',
  *       username: 'supabot'
  *     },
  *     {
  *       onConflict: 'username',
  *       count: 'exact'
  *     }
  *   )
  *
  * // Example response:
  * // {
  * //   data: [
  * //     {
  * //       id: 42,
  * //       handle: "saoirse",
  * //       display_name: "Saoirse"
  * //     }
  * //   ],
  * //   count: 1,
  * //   error: null
  * // }
  * ```
  *
  * @category Database
  *
  * @remarks
  * - Primary keys must be included in `values` to use upsert.
  *
  * @example Upsert your data
  * ```ts
  * const { data, error } = await supabase
  *   .from('instruments')
  *   .upsert({ id: 1, name: 'piano' })
  *   .select()
  * ```
  *
  * @exampleSql Upsert your data
  * ```sql
  * create table
  *   instruments (id int8 primary key, name text);
  *
  * insert into
  *   instruments (id, name)
  * values
  *   (1, 'harpsichord');
  * ```
  *
  * @exampleResponse Upsert your data
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "piano"
  *     }
  *   ],
  *   "status": 201,
  *   "statusText": "Created"
  * }
  * ```
  *
  * @example Bulk Upsert your data
  * ```ts
  * const { data, error } = await supabase
  *   .from('instruments')
  *   .upsert([
  *     { id: 1, name: 'piano' },
  *     { id: 2, name: 'harp' },
  *   ])
  *   .select()
  * ```
  *
  * @exampleSql Bulk Upsert your data
  * ```sql
  * create table
  *   instruments (id int8 primary key, name text);
  *
  * insert into
  *   instruments (id, name)
  * values
  *   (1, 'harpsichord');
  * ```
  *
  * @exampleResponse Bulk Upsert your data
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "piano"
  *     },
  *     {
  *       "id": 2,
  *       "name": "harp"
  *     }
  *   ],
  *   "status": 201,
  *   "statusText": "Created"
  * }
  * ```
  *
  * @exampleDescription Upserting into tables with constraints
  * In the following query, `upsert()` implicitly uses the `id`
  * (primary key) column to determine conflicts. If there is no existing
  * row with the same `id`, `upsert()` inserts a new row, which
  * will fail in this case as there is already a row with `handle` `"saoirse"`.
  * Using the `onConflict` option, you can instruct `upsert()` to use
  * another column with a unique constraint to determine conflicts.
  *
  * @example Upserting into tables with constraints
  * ```ts
  * const { data, error } = await supabase
  *   .from('users')
  *   .upsert({ id: 42, handle: 'saoirse', display_name: 'Saoirse' })
  *   .select()
  * ```
  *
  * @exampleSql Upserting into tables with constraints
  * ```sql
  * create table
  *   users (
  *     id int8 generated by default as identity primary key,
  *     handle text not null unique,
  *     display_name text
  *   );
  *
  * insert into
  *   users (id, handle, display_name)
  * values
  *   (1, 'saoirse', null);
  * ```
  *
  * @exampleResponse Upserting into tables with constraints
  * ```json
  * {
  *   "error": {
  *     "code": "23505",
  *     "details": "Key (handle)=(saoirse) already exists.",
  *     "hint": null,
  *     "message": "duplicate key value violates unique constraint \"users_handle_key\""
  *   },
  *   "status": 409,
  *   "statusText": "Conflict"
  * }
  * ```
  */
  upsert(values, { onConflict, ignoreDuplicates = false, count, defaultToNull = true } = {}) {
    var _this$fetch2;
    const method = "POST";
    const { url, headers } = this.cloneRequestState();
    headers.append("Prefer", `resolution=${ignoreDuplicates ? "ignore" : "merge"}-duplicates`);
    if (onConflict !== void 0) url.searchParams.set("on_conflict", onConflict);
    if (count) headers.append("Prefer", `count=${count}`);
    if (!defaultToNull) headers.append("Prefer", "missing=default");
    if (Array.isArray(values)) {
      const columns = values.reduce((acc, x) => acc.concat(Object.keys(x)), []);
      if (columns.length > 0) {
        const uniqueColumns = [...new Set(columns)].map((column) => `"${column}"`);
        url.searchParams.set("columns", uniqueColumns.join(","));
      }
    }
    return new PostgrestFilterBuilder({
      method,
      url,
      headers,
      schema: this.schema,
      body: values,
      fetch: (_this$fetch2 = this.fetch) !== null && _this$fetch2 !== void 0 ? _this$fetch2 : fetch,
      urlLengthLimit: this.urlLengthLimit,
      retry: this.retry
    });
  }
  /**
  * Perform an UPDATE on the table or view.
  *
  * By default, updated rows are not returned. To return it, chain the call
  * with `.select()` after filters.
  *
  * @param values - The values to update with
  *
  * @param options - Named parameters
  *
  * @param options.count - Count algorithm to use to count updated rows.
  *
  * `"exact"`: Exact but slow count algorithm. Performs a `COUNT(*)` under the
  * hood.
  *
  * `"planned"`: Approximated but fast count algorithm. Uses the Postgres
  * statistics under the hood.
  *
  * `"estimated"`: Uses exact count for low numbers and planned count for high
  * numbers.
  *
  * @category Database
  *
  * @remarks
  * - `update()` should always be combined with [Filters](/docs/reference/javascript/using-filters) to target the item(s) you wish to update.
  *
  * @example Updating your data
  * ```ts
  * const { error } = await supabase
  *   .from('instruments')
  *   .update({ name: 'piano' })
  *   .eq('id', 1)
  * ```
  *
  * @exampleSql Updating your data
  * ```sql
  * create table
  *   instruments (id int8 primary key, name text);
  *
  * insert into
  *   instruments (id, name)
  * values
  *   (1, 'harpsichord');
  * ```
  *
  * @exampleResponse Updating your data
  * ```json
  * {
  *   "status": 204,
  *   "statusText": "No Content"
  * }
  * ```
  *
  * @example Update a record and return it
  * ```ts
  * const { data, error } = await supabase
  *   .from('instruments')
  *   .update({ name: 'piano' })
  *   .eq('id', 1)
  *   .select()
  * ```
  *
  * @exampleSql Update a record and return it
  * ```sql
  * create table
  *   instruments (id int8 primary key, name text);
  *
  * insert into
  *   instruments (id, name)
  * values
  *   (1, 'harpsichord');
  * ```
  *
  * @exampleResponse Update a record and return it
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "piano"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription Updating JSON data
  * Postgres offers some
  * [operators](/docs/guides/database/json#query-the-jsonb-data) for
  * working with JSON data. Currently, it is only possible to update the entire JSON document.
  *
  * @example Updating JSON data
  * ```ts
  * const { data, error } = await supabase
  *   .from('users')
  *   .update({
  *     address: {
  *       street: 'Melrose Place',
  *       postcode: 90210
  *     }
  *   })
  *   .eq('address->postcode', 90210)
  *   .select()
  * ```
  *
  * @exampleSql Updating JSON data
  * ```sql
  * create table
  *   users (
  *     id int8 primary key,
  *     name text,
  *     address jsonb
  *   );
  *
  * insert into
  *   users (id, name, address)
  * values
  *   (1, 'Michael', '{ "postcode": 90210 }');
  * ```
  *
  * @exampleResponse Updating JSON data
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "Michael",
  *       "address": {
  *         "street": "Melrose Place",
  *         "postcode": 90210
  *       }
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  update(values, { count } = {}) {
    var _this$fetch3;
    const method = "PATCH";
    const { url, headers } = this.cloneRequestState();
    if (count) headers.append("Prefer", `count=${count}`);
    return new PostgrestFilterBuilder({
      method,
      url,
      headers,
      schema: this.schema,
      body: values,
      fetch: (_this$fetch3 = this.fetch) !== null && _this$fetch3 !== void 0 ? _this$fetch3 : fetch,
      urlLengthLimit: this.urlLengthLimit,
      retry: this.retry
    });
  }
  /**
  * Perform a DELETE on the table or view.
  *
  * By default, deleted rows are not returned. To return it, chain the call
  * with `.select()` after filters.
  *
  * @param options - Named parameters
  *
  * @param options.count - Count algorithm to use to count deleted rows.
  *
  * `"exact"`: Exact but slow count algorithm. Performs a `COUNT(*)` under the
  * hood.
  *
  * `"planned"`: Approximated but fast count algorithm. Uses the Postgres
  * statistics under the hood.
  *
  * `"estimated"`: Uses exact count for low numbers and planned count for high
  * numbers.
  *
  * @category Database
  *
  * @remarks
  * - `delete()` should always be combined with [filters](/docs/reference/javascript/using-filters) to target the item(s) you wish to delete.
  * - If you use `delete()` with filters and you have
  *   [RLS](/docs/learn/auth-deep-dive/auth-row-level-security) enabled, only
  *   rows visible through `SELECT` policies are deleted. Note that by default
  *   no rows are visible, so you need at least one `SELECT`/`ALL` policy that
  *   makes the rows visible.
  * - When using `delete().in()`, specify an array of values to target multiple rows with a single query. This is particularly useful for batch deleting entries that share common criteria, such as deleting users by their IDs. Ensure that the array you provide accurately represents all records you intend to delete to avoid unintended data removal.
  *
  * @example Delete a single record
  * ```ts
  * const response = await supabase
  *   .from('countries')
  *   .delete()
  *   .eq('id', 1)
  * ```
  *
  * @exampleSql Delete a single record
  * ```sql
  * create table
  *   countries (id int8 primary key, name text);
  *
  * insert into
  *   countries (id, name)
  * values
  *   (1, 'Mordor');
  * ```
  *
  * @exampleResponse Delete a single record
  * ```json
  * {
  *   "status": 204,
  *   "statusText": "No Content"
  * }
  * ```
  *
  * @example Delete a record and return it
  * ```ts
  * const { data, error } = await supabase
  *   .from('countries')
  *   .delete()
  *   .eq('id', 1)
  *   .select()
  * ```
  *
  * @exampleSql Delete a record and return it
  * ```sql
  * create table
  *   countries (id int8 primary key, name text);
  *
  * insert into
  *   countries (id, name)
  * values
  *   (1, 'Mordor');
  * ```
  *
  * @exampleResponse Delete a record and return it
  * ```json
  * {
  *   "data": [
  *     {
  *       "id": 1,
  *       "name": "Mordor"
  *     }
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @example Delete multiple records
  * ```ts
  * const response = await supabase
  *   .from('countries')
  *   .delete()
  *   .in('id', [1, 2, 3])
  * ```
  *
  * @exampleSql Delete multiple records
  * ```sql
  * create table
  *   countries (id int8 primary key, name text);
  *
  * insert into
  *   countries (id, name)
  * values
  *   (1, 'Rohan'), (2, 'The Shire'), (3, 'Mordor');
  * ```
  *
  * @exampleResponse Delete multiple records
  * ```json
  * {
  *   "status": 204,
  *   "statusText": "No Content"
  * }
  * ```
  */
  delete({ count } = {}) {
    var _this$fetch4;
    const method = "DELETE";
    const { url, headers } = this.cloneRequestState();
    if (count) headers.append("Prefer", `count=${count}`);
    return new PostgrestFilterBuilder({
      method,
      url,
      headers,
      schema: this.schema,
      fetch: (_this$fetch4 = this.fetch) !== null && _this$fetch4 !== void 0 ? _this$fetch4 : fetch,
      urlLengthLimit: this.urlLengthLimit,
      retry: this.retry
    });
  }
};
function _typeof(o) {
  "@babel/helpers - typeof";
  return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function(o$1) {
    return typeof o$1;
  } : function(o$1) {
    return o$1 && "function" == typeof Symbol && o$1.constructor === Symbol && o$1 !== Symbol.prototype ? "symbol" : typeof o$1;
  }, _typeof(o);
}
function toPrimitive(t, r) {
  if ("object" != _typeof(t) || !t) return t;
  var e = t[Symbol.toPrimitive];
  if (void 0 !== e) {
    var i = e.call(t, r || "default");
    if ("object" != _typeof(i)) return i;
    throw new TypeError("@@toPrimitive must return a primitive value.");
  }
  return ("string" === r ? String : Number)(t);
}
function toPropertyKey(t) {
  var i = toPrimitive(t, "string");
  return "symbol" == _typeof(i) ? i : i + "";
}
function _defineProperty(e, r, t) {
  return (r = toPropertyKey(r)) in e ? Object.defineProperty(e, r, {
    value: t,
    enumerable: true,
    configurable: true,
    writable: true
  }) : e[r] = t, e;
}
function ownKeys2(e, r) {
  var t = Object.keys(e);
  if (Object.getOwnPropertySymbols) {
    var o = Object.getOwnPropertySymbols(e);
    r && (o = o.filter(function(r$1) {
      return Object.getOwnPropertyDescriptor(e, r$1).enumerable;
    })), t.push.apply(t, o);
  }
  return t;
}
function _objectSpread2(e) {
  for (var r = 1; r < arguments.length; r++) {
    var t = null != arguments[r] ? arguments[r] : {};
    r % 2 ? ownKeys2(Object(t), true).forEach(function(r$1) {
      _defineProperty(e, r$1, t[r$1]);
    }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys2(Object(t)).forEach(function(r$1) {
      Object.defineProperty(e, r$1, Object.getOwnPropertyDescriptor(t, r$1));
    });
  }
  return e;
}
var PostgrestClient = class PostgrestClient2 {
  /**
  * Creates a PostgREST client.
  *
  * @param url - URL of the PostgREST endpoint
  * @param options - Named parameters
  * @param options.headers - Custom headers
  * @param options.schema - Postgres schema to switch to
  * @param options.fetch - Custom fetch
  * @param options.timeout - Optional timeout in milliseconds for all requests. When set, requests will automatically abort after this duration to prevent indefinite hangs.
  * @param options.urlLengthLimit - Maximum URL length in characters before warnings/errors are triggered. Defaults to 8000.
  * @param options.retry - Enable or disable automatic retries for transient errors.
  *   When enabled, idempotent requests (GET, HEAD, OPTIONS) that fail with network
  *   errors or HTTP 503/520 responses will be automatically retried up to 3 times
  *   with exponential backoff (1s, 2s, 4s). Defaults to `true`.
  * @example Using supabase-js (recommended)
  * ```ts
  * import { createClient } from '@supabase/supabase-js'
  *
  * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key')
  * const { data, error } = await supabase.from('profiles').select('*')
  * ```
  *
  * @category Database
  *
  * @remarks
  * - A `timeout` option (in milliseconds) can be set to automatically abort requests that take too long.
  * - A `urlLengthLimit` option (default: 8000) can be set to control when URL length warnings are included in error messages for aborted requests.
  *
  * @example Standalone import for bundle-sensitive environments
  * ```ts
  * import { PostgrestClient } from '@supabase/postgrest-js'
  *
  * const postgrest = new PostgrestClient('https://xyzcompany.supabase.co/rest/v1', {
  *   headers: { apikey: 'publishable-or-anon-key' },
  *   schema: 'public',
  *   timeout: 30000, // 30 second timeout
  * })
  * ```
  */
  constructor(url, { headers = {}, schema, fetch: fetch$1, timeout, urlLengthLimit = 8e3, retry } = {}) {
    this.url = url;
    this.headers = new Headers(headers);
    this.schemaName = schema;
    this.urlLengthLimit = urlLengthLimit;
    const originalFetch = fetch$1 !== null && fetch$1 !== void 0 ? fetch$1 : globalThis.fetch;
    if (timeout !== void 0 && timeout > 0) this.fetch = (input, init) => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);
      const existingSignal = init === null || init === void 0 ? void 0 : init.signal;
      if (existingSignal) {
        if (existingSignal.aborted) {
          clearTimeout(timeoutId);
          return originalFetch(input, init);
        }
        const abortHandler = () => {
          clearTimeout(timeoutId);
          controller.abort();
        };
        existingSignal.addEventListener("abort", abortHandler, { once: true });
        return originalFetch(input, _objectSpread2(_objectSpread2({}, init), {}, { signal: controller.signal })).finally(() => {
          clearTimeout(timeoutId);
          existingSignal.removeEventListener("abort", abortHandler);
        });
      }
      return originalFetch(input, _objectSpread2(_objectSpread2({}, init), {}, { signal: controller.signal })).finally(() => clearTimeout(timeoutId));
    };
    else this.fetch = originalFetch;
    this.retry = retry;
  }
  /**
  * Perform a query on a table or a view.
  *
  * @param relation - The table or view name to query
  *
  * @category Database
  */
  from(relation) {
    if (!relation || typeof relation !== "string" || relation.trim() === "") throw new Error("Invalid relation name: relation must be a non-empty string.");
    return new PostgrestQueryBuilder(new URL(`${this.url}/${relation}`), {
      headers: new Headers(this.headers),
      schema: this.schemaName,
      fetch: this.fetch,
      urlLengthLimit: this.urlLengthLimit,
      retry: this.retry
    });
  }
  /**
  * Select a schema to query or perform an function (rpc) call.
  *
  * The schema needs to be on the list of exposed schemas inside Supabase.
  *
  * @param schema - The schema to query
  *
  * @category Database
  */
  schema(schema) {
    return new PostgrestClient2(this.url, {
      headers: this.headers,
      schema,
      fetch: this.fetch,
      urlLengthLimit: this.urlLengthLimit,
      retry: this.retry
    });
  }
  /**
  * Perform a function call.
  *
  * @param fn - The function name to call
  * @param args - The arguments to pass to the function call
  * @param options - Named parameters
  * @param options.head - When set to `true`, `data` will not be returned.
  * Useful if you only need the count.
  * @param options.get - When set to `true`, the function will be called with
  * read-only access mode.
  * @param options.count - Count algorithm to use to count rows returned by the
  * function. Only applicable for [set-returning
  * functions](https://www.postgresql.org/docs/current/functions-srf.html).
  *
  * `"exact"`: Exact but slow count algorithm. Performs a `COUNT(*)` under the
  * hood.
  *
  * `"planned"`: Approximated but fast count algorithm. Uses the Postgres
  * statistics under the hood.
  *
  * `"estimated"`: Uses exact count for low numbers and planned count for high
  * numbers.
  *
  * @example
  * ```ts
  * // For cross-schema functions where type inference fails, use overrideTypes:
  * const { data } = await supabase
  *   .schema('schema_b')
  *   .rpc('function_a', {})
  *   .overrideTypes<{ id: string; user_id: string }[]>()
  * ```
  *
  * @category Database
  *
  * @example Call a Postgres function without arguments
  * ```ts
  * const { data, error } = await supabase.rpc('hello_world')
  * ```
  *
  * @exampleSql Call a Postgres function without arguments
  * ```sql
  * create function hello_world() returns text as $$
  *   select 'Hello world';
  * $$ language sql;
  * ```
  *
  * @exampleResponse Call a Postgres function without arguments
  * ```json
  * {
  *   "data": "Hello world",
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @example Call a Postgres function with arguments
  * ```ts
  * const { data, error } = await supabase.rpc('echo', { say: '👋' })
  * ```
  *
  * @exampleSql Call a Postgres function with arguments
  * ```sql
  * create function echo(say text) returns text as $$
  *   select say;
  * $$ language sql;
  * ```
  *
  * @exampleResponse Call a Postgres function with arguments
  * ```json
  *   {
  *     "data": "👋",
  *     "status": 200,
  *     "statusText": "OK"
  *   }
  *
  * ```
  *
  * @exampleDescription Bulk processing
  * You can process large payloads by passing in an array as an argument.
  *
  * @example Bulk processing
  * ```ts
  * const { data, error } = await supabase.rpc('add_one_each', { arr: [1, 2, 3] })
  * ```
  *
  * @exampleSql Bulk processing
  * ```sql
  * create function add_one_each(arr int[]) returns int[] as $$
  *   select array_agg(n + 1) from unnest(arr) as n;
  * $$ language sql;
  * ```
  *
  * @exampleResponse Bulk processing
  * ```json
  * {
  *   "data": [
  *     2,
  *     3,
  *     4
  *   ],
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @exampleDescription Call a Postgres function with filters
  * Postgres functions that return tables can also be combined with [Filters](/docs/reference/javascript/using-filters) and [Modifiers](/docs/reference/javascript/using-modifiers).
  *
  * @example Call a Postgres function with filters
  * ```ts
  * const { data, error } = await supabase
  *   .rpc('list_stored_countries')
  *   .eq('id', 1)
  *   .single()
  * ```
  *
  * @exampleSql Call a Postgres function with filters
  * ```sql
  * create table
  *   countries (id int8 primary key, name text);
  *
  * insert into
  *   countries (id, name)
  * values
  *   (1, 'Rohan'),
  *   (2, 'The Shire');
  *
  * create function list_stored_countries() returns setof countries as $$
  *   select * from countries;
  * $$ language sql;
  * ```
  *
  * @exampleResponse Call a Postgres function with filters
  * ```json
  * {
  *   "data": {
  *     "id": 1,
  *     "name": "Rohan"
  *   },
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  *
  * @example Call a read-only Postgres function
  * ```ts
  * const { data, error } = await supabase.rpc('hello_world', undefined, { get: true })
  * ```
  *
  * @exampleSql Call a read-only Postgres function
  * ```sql
  * create function hello_world() returns text as $$
  *   select 'Hello world';
  * $$ language sql;
  * ```
  *
  * @exampleResponse Call a read-only Postgres function
  * ```json
  * {
  *   "data": "Hello world",
  *   "status": 200,
  *   "statusText": "OK"
  * }
  * ```
  */
  rpc(fn, args = {}, { head: head2 = false, get: get2 = false, count } = {}) {
    var _this$fetch;
    let method;
    const url = new URL(`${this.url}/rpc/${fn}`);
    let body;
    const _isObject = (v) => v !== null && typeof v === "object" && (!Array.isArray(v) || v.some(_isObject));
    const _hasObjectArg = head2 && Object.values(args).some(_isObject);
    if (_hasObjectArg) {
      method = "POST";
      body = args;
    } else if (head2 || get2) {
      method = head2 ? "HEAD" : "GET";
      Object.entries(args).filter(([_, value]) => value !== void 0).map(([name, value]) => [name, Array.isArray(value) ? `{${value.join(",")}}` : `${value}`]).forEach(([name, value]) => {
        url.searchParams.append(name, value);
      });
    } else {
      method = "POST";
      body = args;
    }
    const headers = new Headers(this.headers);
    if (_hasObjectArg) headers.set("Prefer", count ? `count=${count},return=minimal` : "return=minimal");
    else if (count) headers.set("Prefer", `count=${count}`);
    return new PostgrestFilterBuilder({
      method,
      url,
      headers,
      schema: this.schemaName,
      body,
      fetch: (_this$fetch = this.fetch) !== null && _this$fetch !== void 0 ? _this$fetch : fetch,
      urlLengthLimit: this.urlLengthLimit,
      retry: this.retry
    });
  }
};

// design/node_modules/@supabase/supabase-js/dist/index.mjs
var import_realtime_js = __toESM(require_main2(), 1);

// design/node_modules/iceberg-js/dist/index.mjs
var IcebergError = class extends Error {
  constructor(message, opts) {
    super(message);
    this.name = "IcebergError";
    this.status = opts.status;
    this.icebergType = opts.icebergType;
    this.icebergCode = opts.icebergCode;
    this.details = opts.details;
    this.isCommitStateUnknown = opts.icebergType === "CommitStateUnknownException" || [500, 502, 504].includes(opts.status) && opts.icebergType?.includes("CommitState") === true;
  }
  /**
   * Returns true if the error is a 404 Not Found error.
   */
  isNotFound() {
    return this.status === 404;
  }
  /**
   * Returns true if the error is a 409 Conflict error.
   */
  isConflict() {
    return this.status === 409;
  }
  /**
   * Returns true if the error is a 419 Authentication Timeout error.
   */
  isAuthenticationTimeout() {
    return this.status === 419;
  }
};
function buildUrl(baseUrl, path, query) {
  const url = new URL(path, baseUrl);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== void 0) {
        url.searchParams.set(key, value);
      }
    }
  }
  return url.toString();
}
async function buildAuthHeaders(auth) {
  if (!auth || auth.type === "none") {
    return {};
  }
  if (auth.type === "bearer") {
    return { Authorization: `Bearer ${auth.token}` };
  }
  if (auth.type === "header") {
    return { [auth.name]: auth.value };
  }
  if (auth.type === "custom") {
    return await auth.getHeaders();
  }
  return {};
}
function createFetchClient(options) {
  const fetchFn = options.fetchImpl ?? globalThis.fetch;
  return {
    async request({
      method,
      path,
      query,
      body,
      headers
    }) {
      const url = buildUrl(options.baseUrl, path, query);
      const authHeaders = await buildAuthHeaders(options.auth);
      const res = await fetchFn(url, {
        method,
        headers: {
          ...body ? { "Content-Type": "application/json" } : {},
          ...authHeaders,
          ...headers
        },
        body: body ? JSON.stringify(body) : void 0
      });
      const text = await res.text();
      const isJson = (res.headers.get("content-type") || "").includes("application/json");
      const data = isJson && text ? JSON.parse(text) : text;
      if (!res.ok) {
        const errBody = isJson ? data : void 0;
        const errorDetail = errBody?.error;
        throw new IcebergError(
          errorDetail?.message ?? `Request failed with status ${res.status}`,
          {
            status: res.status,
            icebergType: errorDetail?.type,
            icebergCode: errorDetail?.code,
            details: errBody
          }
        );
      }
      return { status: res.status, headers: res.headers, data };
    }
  };
}
function namespaceToPath(namespace) {
  return namespace.join("");
}
var NamespaceOperations = class {
  constructor(client, prefix = "") {
    this.client = client;
    this.prefix = prefix;
  }
  async listNamespaces(parent) {
    const query = parent ? { parent: namespaceToPath(parent.namespace) } : void 0;
    const response2 = await this.client.request({
      method: "GET",
      path: `${this.prefix}/namespaces`,
      query
    });
    return response2.data.namespaces.map((ns) => ({ namespace: ns }));
  }
  async createNamespace(id, metadata) {
    const request = {
      namespace: id.namespace,
      properties: metadata?.properties
    };
    const response2 = await this.client.request({
      method: "POST",
      path: `${this.prefix}/namespaces`,
      body: request
    });
    return response2.data;
  }
  async dropNamespace(id) {
    await this.client.request({
      method: "DELETE",
      path: `${this.prefix}/namespaces/${namespaceToPath(id.namespace)}`
    });
  }
  async loadNamespaceMetadata(id) {
    const response2 = await this.client.request({
      method: "GET",
      path: `${this.prefix}/namespaces/${namespaceToPath(id.namespace)}`
    });
    return {
      properties: response2.data.properties
    };
  }
  async namespaceExists(id) {
    try {
      await this.client.request({
        method: "HEAD",
        path: `${this.prefix}/namespaces/${namespaceToPath(id.namespace)}`
      });
      return true;
    } catch (error) {
      if (error instanceof IcebergError && error.status === 404) {
        return false;
      }
      throw error;
    }
  }
  async createNamespaceIfNotExists(id, metadata) {
    try {
      return await this.createNamespace(id, metadata);
    } catch (error) {
      if (error instanceof IcebergError && error.status === 409) {
        return;
      }
      throw error;
    }
  }
};
function namespaceToPath2(namespace) {
  return namespace.join("");
}
var TableOperations = class {
  constructor(client, prefix = "", accessDelegation) {
    this.client = client;
    this.prefix = prefix;
    this.accessDelegation = accessDelegation;
  }
  async listTables(namespace) {
    const response2 = await this.client.request({
      method: "GET",
      path: `${this.prefix}/namespaces/${namespaceToPath2(namespace.namespace)}/tables`
    });
    return response2.data.identifiers;
  }
  async createTable(namespace, request) {
    const headers = {};
    if (this.accessDelegation) {
      headers["X-Iceberg-Access-Delegation"] = this.accessDelegation;
    }
    const response2 = await this.client.request({
      method: "POST",
      path: `${this.prefix}/namespaces/${namespaceToPath2(namespace.namespace)}/tables`,
      body: request,
      headers
    });
    return response2.data.metadata;
  }
  async updateTable(id, request) {
    const response2 = await this.client.request({
      method: "POST",
      path: `${this.prefix}/namespaces/${namespaceToPath2(id.namespace)}/tables/${id.name}`,
      body: request
    });
    return {
      "metadata-location": response2.data["metadata-location"],
      metadata: response2.data.metadata
    };
  }
  async dropTable(id, options) {
    await this.client.request({
      method: "DELETE",
      path: `${this.prefix}/namespaces/${namespaceToPath2(id.namespace)}/tables/${id.name}`,
      query: { purgeRequested: String(options?.purge ?? false) }
    });
  }
  async loadTable(id) {
    const headers = {};
    if (this.accessDelegation) {
      headers["X-Iceberg-Access-Delegation"] = this.accessDelegation;
    }
    const response2 = await this.client.request({
      method: "GET",
      path: `${this.prefix}/namespaces/${namespaceToPath2(id.namespace)}/tables/${id.name}`,
      headers
    });
    return response2.data.metadata;
  }
  async tableExists(id) {
    const headers = {};
    if (this.accessDelegation) {
      headers["X-Iceberg-Access-Delegation"] = this.accessDelegation;
    }
    try {
      await this.client.request({
        method: "HEAD",
        path: `${this.prefix}/namespaces/${namespaceToPath2(id.namespace)}/tables/${id.name}`,
        headers
      });
      return true;
    } catch (error) {
      if (error instanceof IcebergError && error.status === 404) {
        return false;
      }
      throw error;
    }
  }
  async createTableIfNotExists(namespace, request) {
    try {
      return await this.createTable(namespace, request);
    } catch (error) {
      if (error instanceof IcebergError && error.status === 409) {
        return await this.loadTable({ namespace: namespace.namespace, name: request.name });
      }
      throw error;
    }
  }
};
var IcebergRestCatalog = class {
  /**
   * Creates a new Iceberg REST Catalog client.
   *
   * @param options - Configuration options for the catalog client
   */
  constructor(options) {
    let prefix = "v1";
    if (options.catalogName) {
      prefix += `/${options.catalogName}`;
    }
    const baseUrl = options.baseUrl.endsWith("/") ? options.baseUrl : `${options.baseUrl}/`;
    this.client = createFetchClient({
      baseUrl,
      auth: options.auth,
      fetchImpl: options.fetch
    });
    this.accessDelegation = options.accessDelegation?.join(",");
    this.namespaceOps = new NamespaceOperations(this.client, prefix);
    this.tableOps = new TableOperations(this.client, prefix, this.accessDelegation);
  }
  /**
   * Lists all namespaces in the catalog.
   *
   * @param parent - Optional parent namespace to list children under
   * @returns Array of namespace identifiers
   *
   * @example
   * ```typescript
   * // List all top-level namespaces
   * const namespaces = await catalog.listNamespaces();
   *
   * // List namespaces under a parent
   * const children = await catalog.listNamespaces({ namespace: ['analytics'] });
   * ```
   */
  async listNamespaces(parent) {
    return this.namespaceOps.listNamespaces(parent);
  }
  /**
   * Creates a new namespace in the catalog.
   *
   * @param id - Namespace identifier to create
   * @param metadata - Optional metadata properties for the namespace
   * @returns Response containing the created namespace and its properties
   *
   * @example
   * ```typescript
   * const response = await catalog.createNamespace(
   *   { namespace: ['analytics'] },
   *   { properties: { owner: 'data-team' } }
   * );
   * console.log(response.namespace); // ['analytics']
   * console.log(response.properties); // { owner: 'data-team', ... }
   * ```
   */
  async createNamespace(id, metadata) {
    return this.namespaceOps.createNamespace(id, metadata);
  }
  /**
   * Drops a namespace from the catalog.
   *
   * The namespace must be empty (contain no tables) before it can be dropped.
   *
   * @param id - Namespace identifier to drop
   *
   * @example
   * ```typescript
   * await catalog.dropNamespace({ namespace: ['analytics'] });
   * ```
   */
  async dropNamespace(id) {
    await this.namespaceOps.dropNamespace(id);
  }
  /**
   * Loads metadata for a namespace.
   *
   * @param id - Namespace identifier to load
   * @returns Namespace metadata including properties
   *
   * @example
   * ```typescript
   * const metadata = await catalog.loadNamespaceMetadata({ namespace: ['analytics'] });
   * console.log(metadata.properties);
   * ```
   */
  async loadNamespaceMetadata(id) {
    return this.namespaceOps.loadNamespaceMetadata(id);
  }
  /**
   * Lists all tables in a namespace.
   *
   * @param namespace - Namespace identifier to list tables from
   * @returns Array of table identifiers
   *
   * @example
   * ```typescript
   * const tables = await catalog.listTables({ namespace: ['analytics'] });
   * console.log(tables); // [{ namespace: ['analytics'], name: 'events' }, ...]
   * ```
   */
  async listTables(namespace) {
    return this.tableOps.listTables(namespace);
  }
  /**
   * Creates a new table in the catalog.
   *
   * @param namespace - Namespace to create the table in
   * @param request - Table creation request including name, schema, partition spec, etc.
   * @returns Table metadata for the created table
   *
   * @example
   * ```typescript
   * const metadata = await catalog.createTable(
   *   { namespace: ['analytics'] },
   *   {
   *     name: 'events',
   *     schema: {
   *       type: 'struct',
   *       fields: [
   *         { id: 1, name: 'id', type: 'long', required: true },
   *         { id: 2, name: 'timestamp', type: 'timestamp', required: true }
   *       ],
   *       'schema-id': 0
   *     },
   *     'partition-spec': {
   *       'spec-id': 0,
   *       fields: [
   *         { source_id: 2, field_id: 1000, name: 'ts_day', transform: 'day' }
   *       ]
   *     }
   *   }
   * );
   * ```
   */
  async createTable(namespace, request) {
    return this.tableOps.createTable(namespace, request);
  }
  /**
   * Updates an existing table's metadata.
   *
   * Can update the schema, partition spec, or properties of a table.
   *
   * @param id - Table identifier to update
   * @param request - Update request with fields to modify
   * @returns Response containing the metadata location and updated table metadata
   *
   * @example
   * ```typescript
   * const response = await catalog.updateTable(
   *   { namespace: ['analytics'], name: 'events' },
   *   {
   *     properties: { 'read.split.target-size': '134217728' }
   *   }
   * );
   * console.log(response['metadata-location']); // s3://...
   * console.log(response.metadata); // TableMetadata object
   * ```
   */
  async updateTable(id, request) {
    return this.tableOps.updateTable(id, request);
  }
  /**
   * Drops a table from the catalog.
   *
   * @param id - Table identifier to drop
   *
   * @example
   * ```typescript
   * await catalog.dropTable({ namespace: ['analytics'], name: 'events' });
   * ```
   */
  async dropTable(id, options) {
    await this.tableOps.dropTable(id, options);
  }
  /**
   * Loads metadata for a table.
   *
   * @param id - Table identifier to load
   * @returns Table metadata including schema, partition spec, location, etc.
   *
   * @example
   * ```typescript
   * const metadata = await catalog.loadTable({ namespace: ['analytics'], name: 'events' });
   * console.log(metadata.schema);
   * console.log(metadata.location);
   * ```
   */
  async loadTable(id) {
    return this.tableOps.loadTable(id);
  }
  /**
   * Checks if a namespace exists in the catalog.
   *
   * @param id - Namespace identifier to check
   * @returns True if the namespace exists, false otherwise
   *
   * @example
   * ```typescript
   * const exists = await catalog.namespaceExists({ namespace: ['analytics'] });
   * console.log(exists); // true or false
   * ```
   */
  async namespaceExists(id) {
    return this.namespaceOps.namespaceExists(id);
  }
  /**
   * Checks if a table exists in the catalog.
   *
   * @param id - Table identifier to check
   * @returns True if the table exists, false otherwise
   *
   * @example
   * ```typescript
   * const exists = await catalog.tableExists({ namespace: ['analytics'], name: 'events' });
   * console.log(exists); // true or false
   * ```
   */
  async tableExists(id) {
    return this.tableOps.tableExists(id);
  }
  /**
   * Creates a namespace if it does not exist.
   *
   * If the namespace already exists, returns void. If created, returns the response.
   *
   * @param id - Namespace identifier to create
   * @param metadata - Optional metadata properties for the namespace
   * @returns Response containing the created namespace and its properties, or void if it already exists
   *
   * @example
   * ```typescript
   * const response = await catalog.createNamespaceIfNotExists(
   *   { namespace: ['analytics'] },
   *   { properties: { owner: 'data-team' } }
   * );
   * if (response) {
   *   console.log('Created:', response.namespace);
   * } else {
   *   console.log('Already exists');
   * }
   * ```
   */
  async createNamespaceIfNotExists(id, metadata) {
    return this.namespaceOps.createNamespaceIfNotExists(id, metadata);
  }
  /**
   * Creates a table if it does not exist.
   *
   * If the table already exists, returns its metadata instead.
   *
   * @param namespace - Namespace to create the table in
   * @param request - Table creation request including name, schema, partition spec, etc.
   * @returns Table metadata for the created or existing table
   *
   * @example
   * ```typescript
   * const metadata = await catalog.createTableIfNotExists(
   *   { namespace: ['analytics'] },
   *   {
   *     name: 'events',
   *     schema: {
   *       type: 'struct',
   *       fields: [
   *         { id: 1, name: 'id', type: 'long', required: true },
   *         { id: 2, name: 'timestamp', type: 'timestamp', required: true }
   *       ],
   *       'schema-id': 0
   *     }
   *   }
   * );
   * ```
   */
  async createTableIfNotExists(namespace, request) {
    return this.tableOps.createTableIfNotExists(namespace, request);
  }
};

// design/node_modules/@supabase/storage-js/dist/index.mjs
function _typeof2(o) {
  "@babel/helpers - typeof";
  return _typeof2 = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function(o$1) {
    return typeof o$1;
  } : function(o$1) {
    return o$1 && "function" == typeof Symbol && o$1.constructor === Symbol && o$1 !== Symbol.prototype ? "symbol" : typeof o$1;
  }, _typeof2(o);
}
function toPrimitive2(t, r) {
  if ("object" != _typeof2(t) || !t) return t;
  var e = t[Symbol.toPrimitive];
  if (void 0 !== e) {
    var i = e.call(t, r || "default");
    if ("object" != _typeof2(i)) return i;
    throw new TypeError("@@toPrimitive must return a primitive value.");
  }
  return ("string" === r ? String : Number)(t);
}
function toPropertyKey2(t) {
  var i = toPrimitive2(t, "string");
  return "symbol" == _typeof2(i) ? i : i + "";
}
function _defineProperty2(e, r, t) {
  return (r = toPropertyKey2(r)) in e ? Object.defineProperty(e, r, {
    value: t,
    enumerable: true,
    configurable: true,
    writable: true
  }) : e[r] = t, e;
}
function ownKeys3(e, r) {
  var t = Object.keys(e);
  if (Object.getOwnPropertySymbols) {
    var o = Object.getOwnPropertySymbols(e);
    r && (o = o.filter(function(r$1) {
      return Object.getOwnPropertyDescriptor(e, r$1).enumerable;
    })), t.push.apply(t, o);
  }
  return t;
}
function _objectSpread22(e) {
  for (var r = 1; r < arguments.length; r++) {
    var t = null != arguments[r] ? arguments[r] : {};
    r % 2 ? ownKeys3(Object(t), true).forEach(function(r$1) {
      _defineProperty2(e, r$1, t[r$1]);
    }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys3(Object(t)).forEach(function(r$1) {
      Object.defineProperty(e, r$1, Object.getOwnPropertyDescriptor(t, r$1));
    });
  }
  return e;
}
var StorageError = class extends Error {
  constructor(message, namespace = "storage", status, statusCode) {
    super(message);
    this.__isStorageError = true;
    this.namespace = namespace;
    this.name = namespace === "vectors" ? "StorageVectorsError" : "StorageError";
    this.status = status;
    this.statusCode = statusCode;
  }
  toJSON() {
    return {
      name: this.name,
      message: this.message,
      status: this.status,
      statusCode: this.statusCode
    };
  }
};
function isStorageError(error) {
  return typeof error === "object" && error !== null && "__isStorageError" in error;
}
var StorageApiError = class extends StorageError {
  constructor(message, status, statusCode, namespace = "storage") {
    super(message, namespace, status, statusCode);
    this.name = namespace === "vectors" ? "StorageVectorsApiError" : "StorageApiError";
    this.status = status;
    this.statusCode = statusCode;
  }
  toJSON() {
    return _objectSpread22({}, super.toJSON());
  }
};
var StorageUnknownError = class extends StorageError {
  constructor(message, originalError, namespace = "storage") {
    super(message, namespace);
    this.name = namespace === "vectors" ? "StorageVectorsUnknownError" : "StorageUnknownError";
    this.originalError = originalError;
  }
};
function setHeader(headers, name, value) {
  const result = _objectSpread22({}, headers);
  const nameLower = name.toLowerCase();
  for (const key of Object.keys(result)) if (key.toLowerCase() === nameLower) delete result[key];
  result[nameLower] = value;
  return result;
}
function normalizeHeaders(headers) {
  const result = {};
  for (const [key, value] of Object.entries(headers)) result[key.toLowerCase()] = value;
  return result;
}
var resolveFetch = (customFetch) => {
  if (customFetch) return (...args) => customFetch(...args);
  return (...args) => fetch(...args);
};
var isPlainObject = (value) => {
  if (typeof value !== "object" || value === null) return false;
  const prototype = Object.getPrototypeOf(value);
  return (prototype === null || prototype === Object.prototype || Object.getPrototypeOf(prototype) === null) && !(Symbol.toStringTag in value) && !(Symbol.iterator in value);
};
var recursiveToCamel = (item) => {
  if (Array.isArray(item)) return item.map((el) => recursiveToCamel(el));
  else if (typeof item === "function" || item !== Object(item)) return item;
  const result = {};
  Object.entries(item).forEach(([key, value]) => {
    const newKey = key.replace(/([-_][a-z])/gi, (c) => c.toUpperCase().replace(/[-_]/g, ""));
    result[newKey] = recursiveToCamel(value);
  });
  return result;
};
var isValidBucketName = (bucketName) => {
  if (!bucketName || typeof bucketName !== "string") return false;
  if (bucketName.length === 0 || bucketName.length > 100) return false;
  if (bucketName.trim() !== bucketName) return false;
  if (bucketName.includes("/") || bucketName.includes("\\")) return false;
  return /^[\w!.\*'() &$@=;:+,?-]+$/.test(bucketName);
};
var _getErrorMessage = (err) => {
  var _err$error;
  return err.msg || err.message || err.error_description || (typeof err.error === "string" ? err.error : (_err$error = err.error) === null || _err$error === void 0 ? void 0 : _err$error.message) || JSON.stringify(err);
};
var handleError = async (error, reject, options, namespace) => {
  if (error !== null && typeof error === "object" && typeof error.json === "function") {
    const responseError = error;
    let status = parseInt(responseError.status, 10);
    if (!Number.isFinite(status)) status = 500;
    responseError.json().then((err) => {
      const statusCode = (err === null || err === void 0 ? void 0 : err.statusCode) || (err === null || err === void 0 ? void 0 : err.code) || status + "";
      reject(new StorageApiError(_getErrorMessage(err), status, statusCode, namespace));
    }).catch(() => {
      const statusCode = status + "";
      reject(new StorageApiError(responseError.statusText || `HTTP ${status} error`, status, statusCode, namespace));
    });
  } else reject(new StorageUnknownError(_getErrorMessage(error), error, namespace));
};
var _getRequestParams = (method, options, parameters, body) => {
  const params = {
    method,
    headers: (options === null || options === void 0 ? void 0 : options.headers) || {}
  };
  if (method === "GET" || method === "HEAD" || !body) return _objectSpread22(_objectSpread22({}, params), parameters);
  if (isPlainObject(body)) {
    var _contentType;
    const headers = (options === null || options === void 0 ? void 0 : options.headers) || {};
    let contentType;
    for (const [key, value] of Object.entries(headers)) if (key.toLowerCase() === "content-type") contentType = value;
    params.headers = setHeader(headers, "Content-Type", (_contentType = contentType) !== null && _contentType !== void 0 ? _contentType : "application/json");
    params.body = JSON.stringify(body);
  } else params.body = body;
  if (options === null || options === void 0 ? void 0 : options.duplex) params.duplex = options.duplex;
  return _objectSpread22(_objectSpread22({}, params), parameters);
};
async function _handleRequest(fetcher, method, url, options, parameters, body, namespace) {
  return new Promise((resolve, reject) => {
    fetcher(url, _getRequestParams(method, options, parameters, body)).then((result) => {
      if (!result.ok) throw result;
      if (options === null || options === void 0 ? void 0 : options.noResolveJson) return result;
      if (namespace === "vectors") {
        const contentType = result.headers.get("content-type");
        if (result.headers.get("content-length") === "0" || result.status === 204) return {};
        if (!contentType || !contentType.includes("application/json")) return {};
      }
      return result.json();
    }).then((data) => resolve(data)).catch((error) => handleError(error, reject, options, namespace));
  });
}
function createFetchApi(namespace = "storage") {
  return {
    get: async (fetcher, url, options, parameters) => {
      return _handleRequest(fetcher, "GET", url, options, parameters, void 0, namespace);
    },
    post: async (fetcher, url, body, options, parameters) => {
      return _handleRequest(fetcher, "POST", url, options, parameters, body, namespace);
    },
    put: async (fetcher, url, body, options, parameters) => {
      return _handleRequest(fetcher, "PUT", url, options, parameters, body, namespace);
    },
    head: async (fetcher, url, options, parameters) => {
      return _handleRequest(fetcher, "HEAD", url, _objectSpread22(_objectSpread22({}, options), {}, { noResolveJson: true }), parameters, void 0, namespace);
    },
    remove: async (fetcher, url, body, options, parameters) => {
      return _handleRequest(fetcher, "DELETE", url, options, parameters, body, namespace);
    }
  };
}
var defaultApi = createFetchApi("storage");
var { get, post, put, head, remove } = defaultApi;
var vectorsApi = createFetchApi("vectors");
var BaseApiClient = class {
  /**
  * Creates a new BaseApiClient instance
  * @param url - Base URL for API requests
  * @param headers - Default headers for API requests
  * @param fetch - Optional custom fetch implementation
  * @param namespace - Error namespace ('storage' or 'vectors')
  */
  constructor(url, headers = {}, fetch$1, namespace = "storage") {
    this.shouldThrowOnError = false;
    this.url = url;
    this.headers = normalizeHeaders(headers);
    this.fetch = resolveFetch(fetch$1);
    this.namespace = namespace;
  }
  /**
  * Enable throwing errors instead of returning them.
  * When enabled, errors are thrown instead of returned in { data, error } format.
  *
  * @returns this - For method chaining
  */
  throwOnError() {
    this.shouldThrowOnError = true;
    return this;
  }
  /**
  * Set an HTTP header for the request.
  * Creates a shallow copy of headers to avoid mutating shared state.
  *
  * @param name - Header name
  * @param value - Header value
  * @returns this - For method chaining
  */
  setHeader(name, value) {
    this.headers = setHeader(this.headers, name, value);
    return this;
  }
  /**
  * Handles API operation with standardized error handling
  * Eliminates repetitive try-catch blocks across all API methods
  *
  * This wrapper:
  * 1. Executes the operation
  * 2. Returns { data, error: null } on success
  * 3. Returns { data: null, error } on failure (if shouldThrowOnError is false)
  * 4. Throws error on failure (if shouldThrowOnError is true)
  *
  * @typeParam T - The expected data type from the operation
  * @param operation - Async function that performs the API call
  * @returns Promise with { data, error } tuple
  *
  * @example Handling an operation
  * ```typescript
  * async listBuckets() {
  *   return this.handleOperation(async () => {
  *     return await get(this.fetch, `${this.url}/bucket`, {
  *       headers: this.headers,
  *     })
  *   })
  * }
  * ```
  */
  async handleOperation(operation) {
    var _this = this;
    try {
      return {
        data: await operation(),
        error: null
      };
    } catch (error) {
      if (_this.shouldThrowOnError) throw error;
      if (isStorageError(error)) return {
        data: null,
        error
      };
      throw error;
    }
  }
};
var StreamDownloadBuilder = class {
  constructor(downloadFn, shouldThrowOnError) {
    this.downloadFn = downloadFn;
    this.shouldThrowOnError = shouldThrowOnError;
  }
  then(onfulfilled, onrejected) {
    return this.execute().then(onfulfilled, onrejected);
  }
  async execute() {
    var _this = this;
    try {
      return {
        data: (await _this.downloadFn()).body,
        error: null
      };
    } catch (error) {
      if (_this.shouldThrowOnError) throw error;
      if (isStorageError(error)) return {
        data: null,
        error
      };
      throw error;
    }
  }
};
var _Symbol$toStringTag;
_Symbol$toStringTag = Symbol.toStringTag;
var BlobDownloadBuilder = class {
  constructor(downloadFn, shouldThrowOnError) {
    this.downloadFn = downloadFn;
    this.shouldThrowOnError = shouldThrowOnError;
    this[_Symbol$toStringTag] = "BlobDownloadBuilder";
    this.promise = null;
  }
  asStream() {
    return new StreamDownloadBuilder(this.downloadFn, this.shouldThrowOnError);
  }
  then(onfulfilled, onrejected) {
    return this.getPromise().then(onfulfilled, onrejected);
  }
  catch(onrejected) {
    return this.getPromise().catch(onrejected);
  }
  finally(onfinally) {
    return this.getPromise().finally(onfinally);
  }
  getPromise() {
    if (!this.promise) this.promise = this.execute();
    return this.promise;
  }
  async execute() {
    var _this = this;
    try {
      return {
        data: await (await _this.downloadFn()).blob(),
        error: null
      };
    } catch (error) {
      if (_this.shouldThrowOnError) throw error;
      if (isStorageError(error)) return {
        data: null,
        error
      };
      throw error;
    }
  }
};
var DEFAULT_SEARCH_OPTIONS = {
  limit: 100,
  offset: 0,
  sortBy: {
    column: "name",
    order: "asc"
  }
};
var DEFAULT_FILE_OPTIONS = {
  cacheControl: "3600",
  contentType: "text/plain;charset=UTF-8",
  upsert: false
};
var StorageFileApi = class extends BaseApiClient {
  constructor(url, headers = {}, bucketId, fetch$1) {
    super(url, headers, fetch$1, "storage");
    this.bucketId = bucketId;
  }
  /**
  * Uploads a file to an existing bucket or replaces an existing file at the specified path with a new one.
  *
  * @param method HTTP method.
  * @param path The relative file path. Should be of the format `folder/subfolder/filename.png`. The bucket must already exist before attempting to upload.
  * @param fileBody The body of the file to be stored in the bucket.
  */
  async uploadOrUpdate(method, path, fileBody, fileOptions) {
    var _this = this;
    return _this.handleOperation(async () => {
      let body;
      const options = _objectSpread22(_objectSpread22({}, DEFAULT_FILE_OPTIONS), fileOptions);
      let headers = _objectSpread22(_objectSpread22({}, _this.headers), method === "POST" && { "x-upsert": String(options.upsert) });
      const metadata = options.metadata;
      if (typeof Blob !== "undefined" && fileBody instanceof Blob) {
        body = new FormData();
        body.append("cacheControl", options.cacheControl);
        if (metadata) body.append("metadata", _this.encodeMetadata(metadata));
        body.append("", fileBody);
      } else if (typeof FormData !== "undefined" && fileBody instanceof FormData) {
        body = fileBody;
        if (!body.has("cacheControl")) body.append("cacheControl", options.cacheControl);
        if (metadata && !body.has("metadata")) body.append("metadata", _this.encodeMetadata(metadata));
      } else {
        body = fileBody;
        headers["cache-control"] = `max-age=${options.cacheControl}`;
        headers["content-type"] = options.contentType;
        if (metadata) headers["x-metadata"] = _this.toBase64(_this.encodeMetadata(metadata));
        if ((typeof ReadableStream !== "undefined" && body instanceof ReadableStream || body && typeof body === "object" && "pipe" in body && typeof body.pipe === "function") && !options.duplex) options.duplex = "half";
      }
      if (fileOptions === null || fileOptions === void 0 ? void 0 : fileOptions.headers) for (const [key, value] of Object.entries(fileOptions.headers)) headers = setHeader(headers, key, value);
      const cleanPath = _this._removeEmptyFolders(path);
      const _path = _this._getFinalPath(cleanPath);
      const data = await (method == "PUT" ? put : post)(_this.fetch, `${_this.url}/object/${_path}`, body, _objectSpread22({ headers }, (options === null || options === void 0 ? void 0 : options.duplex) ? { duplex: options.duplex } : {}));
      return {
        path: cleanPath,
        id: data.Id,
        fullPath: data.Key
      };
    });
  }
  /**
  * Uploads a file to an existing bucket.
  *
  * @category File Buckets
  * @param path The file path, including the file name. Should be of the format `folder/subfolder/filename.png`. The bucket must already exist before attempting to upload.
  * @param fileBody The body of the file to be stored in the bucket.
  * @param fileOptions Optional file upload options including cacheControl, contentType, upsert, and metadata.
  * @returns Promise with response containing file path, id, and fullPath or error
  *
  * @example Upload file
  * ```js
  * const avatarFile = event.target.files[0]
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .upload('public/avatar1.png', avatarFile, {
  *     cacheControl: '3600',
  *     upsert: false
  *   })
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "path": "public/avatar1.png",
  *     "fullPath": "avatars/public/avatar1.png"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @example Upload file using `ArrayBuffer` from base64 file data
  * ```js
  * import { decode } from 'base64-arraybuffer'
  *
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .upload('public/avatar1.png', decode('base64FileData'), {
  *     contentType: 'image/png'
  *   })
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: none
  *   - `objects` table permissions: only `insert` when you are uploading new files and `select`, `insert` and `update` when you are upserting files
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  * - For React Native, using either `Blob`, `File` or `FormData` does not work as intended. Upload file using `ArrayBuffer` from base64 file data instead, see example below.
  */
  async upload(path, fileBody, fileOptions) {
    return this.uploadOrUpdate("POST", path, fileBody, fileOptions);
  }
  /**
  * Upload a file with a token generated from `createSignedUploadUrl`.
  *
  * @category File Buckets
  * @param path The file path, including the file name. Should be of the format `folder/subfolder/filename.png`. The bucket must already exist before attempting to upload.
  * @param token The token generated from `createSignedUploadUrl`
  * @param fileBody The body of the file to be stored in the bucket.
  * @param fileOptions HTTP headers (cacheControl, contentType, etc.).
  * **Note:** The `upsert` option has no effect here. To enable upsert behavior,
  * pass `{ upsert: true }` when calling `createSignedUploadUrl()` instead.
  * @returns Promise with response containing file path and fullPath or error
  *
  * @example Upload to a signed URL
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .uploadToSignedUrl('folder/cat.jpg', 'token-from-createSignedUploadUrl', file)
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "path": "folder/cat.jpg",
  *     "fullPath": "avatars/folder/cat.jpg"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: none
  *   - `objects` table permissions: none
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async uploadToSignedUrl(path, token, fileBody, fileOptions) {
    var _this3 = this;
    const cleanPath = _this3._removeEmptyFolders(path);
    const _path = _this3._getFinalPath(cleanPath);
    const url = new URL(_this3.url + `/object/upload/sign/${_path}`);
    url.searchParams.set("token", token);
    return _this3.handleOperation(async () => {
      let body;
      const options = _objectSpread22(_objectSpread22({}, DEFAULT_FILE_OPTIONS), fileOptions);
      const headers = _objectSpread22(_objectSpread22({}, _this3.headers), { "x-upsert": String(options.upsert) });
      if (typeof Blob !== "undefined" && fileBody instanceof Blob) {
        body = new FormData();
        body.append("cacheControl", options.cacheControl);
        body.append("", fileBody);
      } else if (typeof FormData !== "undefined" && fileBody instanceof FormData) {
        body = fileBody;
        body.append("cacheControl", options.cacheControl);
      } else {
        body = fileBody;
        headers["cache-control"] = `max-age=${options.cacheControl}`;
        headers["content-type"] = options.contentType;
      }
      return {
        path: cleanPath,
        fullPath: (await put(_this3.fetch, url.toString(), body, { headers })).Key
      };
    });
  }
  /**
  * Creates a signed upload URL.
  * Signed upload URLs can be used to upload files to the bucket without further authentication.
  * They are valid for 2 hours.
  *
  * @category File Buckets
  * @param path The file path, including the current file name. For example `folder/image.png`.
  * @param options.upsert If set to true, allows the file to be overwritten if it already exists.
  * @returns Promise with response containing signed upload URL, token, and path or error
  *
  * @example Create Signed Upload URL
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .createSignedUploadUrl('folder/cat.jpg')
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "signedUrl": "https://example.supabase.co/storage/v1/object/upload/sign/avatars/folder/cat.jpg?token=<TOKEN>",
  *     "path": "folder/cat.jpg",
  *     "token": "<TOKEN>"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: none
  *   - `objects` table permissions: `insert`
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async createSignedUploadUrl(path, options) {
    var _this4 = this;
    return _this4.handleOperation(async () => {
      let _path = _this4._getFinalPath(path);
      const headers = _objectSpread22({}, _this4.headers);
      if (options === null || options === void 0 ? void 0 : options.upsert) headers["x-upsert"] = "true";
      const data = await post(_this4.fetch, `${_this4.url}/object/upload/sign/${_path}`, {}, { headers });
      const url = new URL(_this4.url + data.url);
      const token = url.searchParams.get("token");
      if (!token) throw new StorageError("No token returned by API");
      return {
        signedUrl: url.toString(),
        path,
        token
      };
    });
  }
  /**
  * Replaces an existing file at the specified path with a new one.
  *
  * @category File Buckets
  * @param path The relative file path. Should be of the format `folder/subfolder/filename.png`. The bucket must already exist before attempting to update.
  * @param fileBody The body of the file to be stored in the bucket.
  * @param fileOptions Optional file upload options including cacheControl, contentType, upsert, and metadata.
  * @returns Promise with response containing file path, id, and fullPath or error
  *
  * @example Update file
  * ```js
  * const avatarFile = event.target.files[0]
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .update('public/avatar1.png', avatarFile, {
  *     cacheControl: '3600',
  *     upsert: true
  *   })
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "path": "public/avatar1.png",
  *     "fullPath": "avatars/public/avatar1.png"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @example Update file using `ArrayBuffer` from base64 file data
  * ```js
  * import {decode} from 'base64-arraybuffer'
  *
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .update('public/avatar1.png', decode('base64FileData'), {
  *     contentType: 'image/png'
  *   })
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: none
  *   - `objects` table permissions: `update` and `select`
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  * - For React Native, using either `Blob`, `File` or `FormData` does not work as intended. Update file using `ArrayBuffer` from base64 file data instead, see example below.
  */
  async update(path, fileBody, fileOptions) {
    return this.uploadOrUpdate("PUT", path, fileBody, fileOptions);
  }
  /**
  * Moves an existing file to a new path in the same bucket.
  *
  * @category File Buckets
  * @param fromPath The original file path, including the current file name. For example `folder/image.png`.
  * @param toPath The new file path, including the new file name. For example `folder/image-new.png`.
  * @param options The destination options.
  * @returns Promise with response containing success message or error
  *
  * @example Move file
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .move('public/avatar1.png', 'private/avatar2.png')
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "message": "Successfully moved"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: none
  *   - `objects` table permissions: `update` and `select`
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async move(fromPath, toPath, options) {
    var _this6 = this;
    return _this6.handleOperation(async () => {
      return await post(_this6.fetch, `${_this6.url}/object/move`, {
        bucketId: _this6.bucketId,
        sourceKey: fromPath,
        destinationKey: toPath,
        destinationBucket: options === null || options === void 0 ? void 0 : options.destinationBucket
      }, { headers: _this6.headers });
    });
  }
  /**
  * Copies an existing file to a new path in the same bucket.
  *
  * @category File Buckets
  * @param fromPath The original file path, including the current file name. For example `folder/image.png`.
  * @param toPath The new file path, including the new file name. For example `folder/image-copy.png`.
  * @param options The destination options.
  * @returns Promise with response containing copied file path or error
  *
  * @example Copy file
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .copy('public/avatar1.png', 'private/avatar2.png')
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "path": "avatars/private/avatar2.png"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: none
  *   - `objects` table permissions: `insert` and `select`
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async copy(fromPath, toPath, options) {
    var _this7 = this;
    return _this7.handleOperation(async () => {
      return { path: (await post(_this7.fetch, `${_this7.url}/object/copy`, {
        bucketId: _this7.bucketId,
        sourceKey: fromPath,
        destinationKey: toPath,
        destinationBucket: options === null || options === void 0 ? void 0 : options.destinationBucket
      }, { headers: _this7.headers })).Key };
    });
  }
  /**
  * Creates a signed URL. Use a signed URL to share a file for a fixed amount of time.
  *
  * @category File Buckets
  * @param path The file path, including the current file name. For example `folder/image.png`.
  * @param expiresIn The number of seconds until the signed URL expires. For example, `60` for a URL which is valid for one minute.
  * @param options.download triggers the file as a download if set to true. Set this parameter as the name of the file if you want to trigger the download with a different filename.
  * @param options.transform Transform the asset before serving it to the client.
  * @param options.cacheNonce Append a cache nonce parameter to the URL to invalidate the cache.
  * @returns Promise with response containing signed URL or error
  *
  * @example Create Signed URL
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .createSignedUrl('folder/avatar1.png', 60)
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "signedUrl": "https://example.supabase.co/storage/v1/object/sign/avatars/folder/avatar1.png?token=<TOKEN>"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @example Create a signed URL for an asset with transformations
  * ```js
  * const { data } = await supabase
  *   .storage
  *   .from('avatars')
  *   .createSignedUrl('folder/avatar1.png', 60, {
  *     transform: {
  *       width: 100,
  *       height: 100,
  *     }
  *   })
  * ```
  *
  * @example Create a signed URL which triggers the download of the asset
  * ```js
  * const { data } = await supabase
  *   .storage
  *   .from('avatars')
  *   .createSignedUrl('folder/avatar1.png', 60, {
  *     download: true,
  *   })
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: none
  *   - `objects` table permissions: `select`
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async createSignedUrl(path, expiresIn, options) {
    var _this8 = this;
    return _this8.handleOperation(async () => {
      let _path = _this8._getFinalPath(path);
      const hasTransform = typeof (options === null || options === void 0 ? void 0 : options.transform) === "object" && options.transform !== null && Object.keys(options.transform).length > 0;
      let data = await post(_this8.fetch, `${_this8.url}/object/sign/${_path}`, _objectSpread22({ expiresIn }, hasTransform ? { transform: options.transform } : {}), { headers: _this8.headers });
      const query = new URLSearchParams();
      if (options === null || options === void 0 ? void 0 : options.download) query.set("download", options.download === true ? "" : options.download);
      if ((options === null || options === void 0 ? void 0 : options.cacheNonce) != null) query.set("cacheNonce", String(options.cacheNonce));
      const queryString = query.toString();
      return { signedUrl: encodeURI(`${_this8.url}${data.signedURL}${queryString ? `&${queryString}` : ""}`) };
    });
  }
  /**
  * Creates multiple signed URLs. Use a signed URL to share a file for a fixed amount of time.
  *
  * @category File Buckets
  * @param paths The file paths to be downloaded, including the current file names. For example `['folder/image.png', 'folder2/image2.png']`.
  * @param expiresIn The number of seconds until the signed URLs expire. For example, `60` for URLs which are valid for one minute.
  * @param options.download triggers the file as a download if set to true. Set this parameter as the name of the file if you want to trigger the download with a different filename.
  * @param options.cacheNonce Append a cache nonce parameter to the URL to invalidate the cache.
  * @returns Promise with response containing array of objects with signedUrl, path, and error or error
  *
  * @example Create Signed URLs
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .createSignedUrls(['folder/avatar1.png', 'folder/avatar2.png'], 60)
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": [
  *     {
  *       "error": null,
  *       "path": "folder/avatar1.png",
  *       "signedURL": "/object/sign/avatars/folder/avatar1.png?token=<TOKEN>",
  *       "signedUrl": "https://example.supabase.co/storage/v1/object/sign/avatars/folder/avatar1.png?token=<TOKEN>"
  *     },
  *     {
  *       "error": null,
  *       "path": "folder/avatar2.png",
  *       "signedURL": "/object/sign/avatars/folder/avatar2.png?token=<TOKEN>",
  *       "signedUrl": "https://example.supabase.co/storage/v1/object/sign/avatars/folder/avatar2.png?token=<TOKEN>"
  *     }
  *   ],
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: none
  *   - `objects` table permissions: `select`
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async createSignedUrls(paths, expiresIn, options) {
    var _this9 = this;
    return _this9.handleOperation(async () => {
      const data = await post(_this9.fetch, `${_this9.url}/object/sign/${_this9.bucketId}`, {
        expiresIn,
        paths
      }, { headers: _this9.headers });
      const query = new URLSearchParams();
      if (options === null || options === void 0 ? void 0 : options.download) query.set("download", options.download === true ? "" : options.download);
      if ((options === null || options === void 0 ? void 0 : options.cacheNonce) != null) query.set("cacheNonce", String(options.cacheNonce));
      const queryString = query.toString();
      return data.map((datum) => _objectSpread22(_objectSpread22({}, datum), {}, { signedUrl: datum.signedURL ? encodeURI(`${_this9.url}${datum.signedURL}${queryString ? `&${queryString}` : ""}`) : null }));
    });
  }
  /**
  * Downloads a file from a private bucket. For public buckets, make a request to the URL returned from `getPublicUrl` instead.
  *
  * @category File Buckets
  * @param path The full path and file name of the file to be downloaded. For example `folder/image.png`.
  * @param options.transform Transform the asset before serving it to the client.
  * @param options.cacheNonce Append a cache nonce parameter to the URL to invalidate the cache.
  * @param parameters Additional fetch parameters like signal for cancellation. Supports standard fetch options including cache control.
  * @returns BlobDownloadBuilder instance for downloading the file
  *
  * @example Download file
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .download('folder/avatar1.png')
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": <BLOB>,
  *   "error": null
  * }
  * ```
  *
  * @example Download file with transformations
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .download('folder/avatar1.png', {
  *     transform: {
  *       width: 100,
  *       height: 100,
  *       quality: 80
  *     }
  *   })
  * ```
  *
  * @example Download with cache control (useful in Edge Functions)
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .download('folder/avatar1.png', {}, { cache: 'no-store' })
  * ```
  *
  * @example Download with abort signal
  * ```js
  * const controller = new AbortController()
  * setTimeout(() => controller.abort(), 5000)
  *
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .download('folder/avatar1.png', {}, { signal: controller.signal })
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: none
  *   - `objects` table permissions: `select`
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  download(path, options, parameters) {
    const renderPath = typeof (options === null || options === void 0 ? void 0 : options.transform) === "object" && options.transform !== null && Object.keys(options.transform).length > 0 ? "render/image/authenticated" : "object";
    const query = new URLSearchParams();
    if (options === null || options === void 0 ? void 0 : options.transform) this.applyTransformOptsToQuery(query, options.transform);
    if ((options === null || options === void 0 ? void 0 : options.cacheNonce) != null) query.set("cacheNonce", String(options.cacheNonce));
    const queryString = query.toString();
    const _path = this._getFinalPath(path);
    const downloadFn = () => get(this.fetch, `${this.url}/${renderPath}/${_path}${queryString ? `?${queryString}` : ""}`, {
      headers: this.headers,
      noResolveJson: true
    }, parameters);
    return new BlobDownloadBuilder(downloadFn, this.shouldThrowOnError);
  }
  /**
  * Retrieves the details of an existing file.
  *
  * Returns detailed file metadata including size, content type, and timestamps.
  * Note: The API returns `last_modified` field, not `updated_at`.
  *
  * @category File Buckets
  * @param path The file path, including the file name. For example `folder/image.png`.
  * @returns Promise with response containing file metadata or error
  *
  * @example Get file info
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .info('folder/avatar1.png')
  *
  * if (data) {
  *   console.log('Last modified:', data.lastModified)
  *   console.log('Size:', data.size)
  * }
  * ```
  */
  async info(path) {
    var _this10 = this;
    const _path = _this10._getFinalPath(path);
    return _this10.handleOperation(async () => {
      return recursiveToCamel(await get(_this10.fetch, `${_this10.url}/object/info/${_path}`, { headers: _this10.headers }));
    });
  }
  /**
  * Checks the existence of a file.
  *
  * @category File Buckets
  * @param path The file path, including the file name. For example `folder/image.png`.
  * @returns Promise with response containing boolean indicating file existence or error
  *
  * @example Check file existence
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .exists('folder/avatar1.png')
  * ```
  */
  async exists(path) {
    var _this11 = this;
    const _path = _this11._getFinalPath(path);
    try {
      await head(_this11.fetch, `${_this11.url}/object/${_path}`, { headers: _this11.headers });
      return {
        data: true,
        error: null
      };
    } catch (error) {
      if (_this11.shouldThrowOnError) throw error;
      if (isStorageError(error)) {
        var _error$originalError;
        const status = error instanceof StorageApiError ? error.status : error instanceof StorageUnknownError ? (_error$originalError = error.originalError) === null || _error$originalError === void 0 ? void 0 : _error$originalError.status : void 0;
        if (status !== void 0 && [400, 404].includes(status)) return {
          data: false,
          error
        };
      }
      throw error;
    }
  }
  /**
  * A simple convenience function to get the URL for an asset in a public bucket. If you do not want to use this function, you can construct the public URL by concatenating the bucket URL with the path to the asset.
  * This function does not verify if the bucket is public. If a public URL is created for a bucket which is not public, you will not be able to download the asset.
  *
  * @category File Buckets
  * @param path The path and name of the file to generate the public URL for. For example `folder/image.png`.
  * @param options.download Triggers the file as a download if set to true. Set this parameter as the name of the file if you want to trigger the download with a different filename.
  * @param options.transform Transform the asset before serving it to the client.
  * @param options.cacheNonce Append a cache nonce parameter to the URL to invalidate the cache.
  * @returns Object with public URL
  *
  * @example Returns the URL for an asset in a public bucket
  * ```js
  * const { data } = supabase
  *   .storage
  *   .from('public-bucket')
  *   .getPublicUrl('folder/avatar1.png')
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "publicUrl": "https://example.supabase.co/storage/v1/object/public/public-bucket/folder/avatar1.png"
  *   }
  * }
  * ```
  *
  * @example Returns the URL for an asset in a public bucket with transformations
  * ```js
  * const { data } = supabase
  *   .storage
  *   .from('public-bucket')
  *   .getPublicUrl('folder/avatar1.png', {
  *     transform: {
  *       width: 100,
  *       height: 100,
  *     }
  *   })
  * ```
  *
  * @example Returns the URL which triggers the download of an asset in a public bucket
  * ```js
  * const { data } = supabase
  *   .storage
  *   .from('public-bucket')
  *   .getPublicUrl('folder/avatar1.png', {
  *     download: true,
  *   })
  * ```
  *
  * @remarks
  * - The bucket needs to be set to public, either via [updateBucket()](/docs/reference/javascript/storage-updatebucket) or by going to Storage on [supabase.com/dashboard](https://supabase.com/dashboard), clicking the overflow menu on a bucket and choosing "Make public"
  * - RLS policy permissions required:
  *   - `buckets` table permissions: none
  *   - `objects` table permissions: none
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  getPublicUrl(path, options) {
    const _path = this._getFinalPath(path);
    const query = new URLSearchParams();
    if (options === null || options === void 0 ? void 0 : options.download) query.set("download", options.download === true ? "" : options.download);
    if (options === null || options === void 0 ? void 0 : options.transform) this.applyTransformOptsToQuery(query, options.transform);
    if ((options === null || options === void 0 ? void 0 : options.cacheNonce) != null) query.set("cacheNonce", String(options.cacheNonce));
    const queryString = query.toString();
    const renderPath = typeof (options === null || options === void 0 ? void 0 : options.transform) === "object" && options.transform !== null && Object.keys(options.transform).length > 0 ? "render/image" : "object";
    return { data: { publicUrl: encodeURI(`${this.url}/${renderPath}/public/${_path}`) + (queryString ? `?${queryString}` : "") } };
  }
  /**
  * Deletes files within the same bucket
  *
  * Returns an array of FileObject entries for the deleted files. Note that deprecated
  * fields like `bucket_id` may or may not be present in the response - do not rely on them.
  *
  * @category File Buckets
  * @param paths An array of files to delete, including the path and file name. For example [`'folder/image.png'`].
  * @returns Promise with response containing array of deleted file objects or error
  *
  * @example Delete file
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .remove(['folder/avatar1.png'])
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": [],
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: none
  *   - `objects` table permissions: `delete` and `select`
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async remove(paths) {
    var _this12 = this;
    return _this12.handleOperation(async () => {
      return await remove(_this12.fetch, `${_this12.url}/object/${_this12.bucketId}`, { prefixes: paths }, { headers: _this12.headers });
    });
  }
  /**
  * Get file metadata
  * @param id the file id to retrieve metadata
  */
  /**
  * Update file metadata
  * @param id the file id to update metadata
  * @param meta the new file metadata
  */
  /**
  * Lists all the files and folders within a path of the bucket.
  *
  * **Important:** For folder entries, fields like `id`, `updated_at`, `created_at`,
  * `last_accessed_at`, and `metadata` will be `null`. Only files have these fields populated.
  * Additionally, deprecated fields like `bucket_id`, `owner`, and `buckets` are NOT returned
  * by this method.
  *
  * @category File Buckets
  * @param path The folder path.
  * @param options Search options including limit (defaults to 100), offset, sortBy, and search
  * @param parameters Optional fetch parameters including signal for cancellation
  * @returns Promise with response containing array of files/folders or error
  *
  * @example List files in a bucket
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .list('folder', {
  *     limit: 100,
  *     offset: 0,
  *     sortBy: { column: 'name', order: 'asc' },
  *   })
  *
  * // Handle files vs folders
  * data?.forEach(item => {
  *   if (item.id !== null) {
  *     // It's a file
  *     console.log('File:', item.name, 'Size:', item.metadata?.size)
  *   } else {
  *     // It's a folder
  *     console.log('Folder:', item.name)
  *   }
  * })
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "avatar1.png",
  *       "id": "e668cf7f-821b-4a2f-9dce-7dfa5dd1cfd2",
  *       "updated_at": "2024-05-22T23:06:05.580Z",
  *       "created_at": "2024-05-22T23:04:34.443Z",
  *       "last_accessed_at": "2024-05-22T23:04:34.443Z",
  *       "metadata": {
  *         "eTag": "\"c5e8c553235d9af30ef4f6e280790b92\"",
  *         "size": 32175,
  *         "mimetype": "image/png",
  *         "cacheControl": "max-age=3600",
  *         "lastModified": "2024-05-22T23:06:05.574Z",
  *         "contentLength": 32175,
  *         "httpStatusCode": 200
  *       }
  *     }
  *   ],
  *   "error": null
  * }
  * ```
  *
  * @example Search files in a bucket
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .list('folder', {
  *     limit: 100,
  *     offset: 0,
  *     sortBy: { column: 'name', order: 'asc' },
  *     search: 'jon'
  *   })
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: none
  *   - `objects` table permissions: `select`
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async list(path, options, parameters) {
    var _this13 = this;
    return _this13.handleOperation(async () => {
      const body = _objectSpread22(_objectSpread22(_objectSpread22({}, DEFAULT_SEARCH_OPTIONS), options), {}, { prefix: path || "" });
      return await post(_this13.fetch, `${_this13.url}/object/list/${_this13.bucketId}`, body, { headers: _this13.headers }, parameters);
    });
  }
  /**
  * Lists all the files and folders within a bucket using the V2 API with pagination support.
  *
  * **Important:** Folder entries in the `folders` array only contain `name` and optionally `key` —
  * they have no `id`, timestamps, or `metadata` fields. Full file metadata is only available
  * on entries in the `objects` array.
  *
  * @experimental this method signature might change in the future
  *
  * @category File Buckets
  * @param options Search options including prefix, cursor for pagination, limit, with_delimiter
  * @param parameters Optional fetch parameters including signal for cancellation
  * @returns Promise with response containing folders/objects arrays with pagination info or error
  *
  * @example List files with pagination
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .from('avatars')
  *   .listV2({
  *     prefix: 'folder/',
  *     limit: 100,
  *   })
  *
  * // Handle pagination
  * if (data?.hasNext) {
  *   const nextPage = await supabase
  *     .storage
  *     .from('avatars')
  *     .listV2({
  *       prefix: 'folder/',
  *       cursor: data.nextCursor,
  *     })
  * }
  *
  * // Handle files vs folders
  * data?.objects.forEach(file => {
  *   if (file.id !== null) {
  *     console.log('File:', file.name, 'Size:', file.metadata?.size)
  *   }
  * })
  * data?.folders.forEach(folder => {
  *   console.log('Folder:', folder.name)
  * })
  * ```
  */
  async listV2(options, parameters) {
    var _this14 = this;
    return _this14.handleOperation(async () => {
      const body = _objectSpread22({}, options);
      return await post(_this14.fetch, `${_this14.url}/object/list-v2/${_this14.bucketId}`, body, { headers: _this14.headers }, parameters);
    });
  }
  encodeMetadata(metadata) {
    return JSON.stringify(metadata);
  }
  toBase64(data) {
    if (typeof Buffer !== "undefined") return Buffer.from(data).toString("base64");
    return btoa(data);
  }
  _getFinalPath(path) {
    return `${this.bucketId}/${path.replace(/^\/+/, "")}`;
  }
  _removeEmptyFolders(path) {
    return path.replace(/^\/|\/$/g, "").replace(/\/+/g, "/");
  }
  /** Modifies the `query`, appending values the from `transform` */
  applyTransformOptsToQuery(query, transform) {
    if (transform.width) query.set("width", transform.width.toString());
    if (transform.height) query.set("height", transform.height.toString());
    if (transform.resize) query.set("resize", transform.resize);
    if (transform.format) query.set("format", transform.format);
    if (transform.quality) query.set("quality", transform.quality.toString());
    return query;
  }
};
var version = "2.104.1";
var DEFAULT_HEADERS = { "X-Client-Info": `storage-js/${version}` };
var StorageBucketApi = class extends BaseApiClient {
  constructor(url, headers = {}, fetch$1, opts) {
    const baseUrl = new URL(url);
    if (opts === null || opts === void 0 ? void 0 : opts.useNewHostname) {
      if (/supabase\.(co|in|red)$/.test(baseUrl.hostname) && !baseUrl.hostname.includes("storage.supabase.")) baseUrl.hostname = baseUrl.hostname.replace("supabase.", "storage.supabase.");
    }
    const finalUrl = baseUrl.href.replace(/\/$/, "");
    const finalHeaders = _objectSpread22(_objectSpread22({}, DEFAULT_HEADERS), headers);
    super(finalUrl, finalHeaders, fetch$1, "storage");
  }
  /**
  * Retrieves the details of all Storage buckets within an existing project.
  *
  * @category File Buckets
  * @param options Query parameters for listing buckets
  * @param options.limit Maximum number of buckets to return
  * @param options.offset Number of buckets to skip
  * @param options.sortColumn Column to sort by ('id', 'name', 'created_at', 'updated_at')
  * @param options.sortOrder Sort order ('asc' or 'desc')
  * @param options.search Search term to filter bucket names
  * @returns Promise with response containing array of buckets or error
  *
  * @example List buckets
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .listBuckets()
  * ```
  *
  * @example List buckets with options
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .listBuckets({
  *     limit: 10,
  *     offset: 0,
  *     sortColumn: 'created_at',
  *     sortOrder: 'desc',
  *     search: 'prod'
  *   })
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: `select`
  *   - `objects` table permissions: none
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async listBuckets(options) {
    var _this = this;
    return _this.handleOperation(async () => {
      const queryString = _this.listBucketOptionsToQueryString(options);
      return await get(_this.fetch, `${_this.url}/bucket${queryString}`, { headers: _this.headers });
    });
  }
  /**
  * Retrieves the details of an existing Storage bucket.
  *
  * @category File Buckets
  * @param id The unique identifier of the bucket you would like to retrieve.
  * @returns Promise with response containing bucket details or error
  *
  * @example Get bucket
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .getBucket('avatars')
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "id": "avatars",
  *     "name": "avatars",
  *     "owner": "",
  *     "public": false,
  *     "file_size_limit": 1024,
  *     "allowed_mime_types": [
  *       "image/png"
  *     ],
  *     "created_at": "2024-05-22T22:26:05.100Z",
  *     "updated_at": "2024-05-22T22:26:05.100Z"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: `select`
  *   - `objects` table permissions: none
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async getBucket(id) {
    var _this2 = this;
    return _this2.handleOperation(async () => {
      return await get(_this2.fetch, `${_this2.url}/bucket/${id}`, { headers: _this2.headers });
    });
  }
  /**
  * Creates a new Storage bucket
  *
  * @category File Buckets
  * @param id A unique identifier for the bucket you are creating.
  * @param options.public The visibility of the bucket. Public buckets don't require an authorization token to download objects, but still require a valid token for all other operations. By default, buckets are private.
  * @param options.fileSizeLimit specifies the max file size in bytes that can be uploaded to this bucket.
  * The global file size limit takes precedence over this value.
  * The default value is null, which doesn't set a per bucket file size limit.
  * @param options.allowedMimeTypes specifies the allowed mime types that this bucket can accept during upload.
  * The default value is null, which allows files with all mime types to be uploaded.
  * Each mime type specified can be a wildcard, e.g. image/*, or a specific mime type, e.g. image/png.
  * @param options.type (private-beta) specifies the bucket type. see `BucketType` for more details.
  *   - default bucket type is `STANDARD`
  * @returns Promise with response containing newly created bucket name or error
  *
  * @example Create bucket
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .createBucket('avatars', {
  *     public: false,
  *     allowedMimeTypes: ['image/png'],
  *     fileSizeLimit: 1024
  *   })
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "name": "avatars"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: `insert`
  *   - `objects` table permissions: none
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async createBucket(id, options = { public: false }) {
    var _this3 = this;
    return _this3.handleOperation(async () => {
      return await post(_this3.fetch, `${_this3.url}/bucket`, {
        id,
        name: id,
        type: options.type,
        public: options.public,
        file_size_limit: options.fileSizeLimit,
        allowed_mime_types: options.allowedMimeTypes
      }, { headers: _this3.headers });
    });
  }
  /**
  * Updates a Storage bucket
  *
  * @category File Buckets
  * @param id A unique identifier for the bucket you are updating.
  * @param options.public The visibility of the bucket. Public buckets don't require an authorization token to download objects, but still require a valid token for all other operations.
  * @param options.fileSizeLimit specifies the max file size in bytes that can be uploaded to this bucket.
  * The global file size limit takes precedence over this value.
  * The default value is null, which doesn't set a per bucket file size limit.
  * @param options.allowedMimeTypes specifies the allowed mime types that this bucket can accept during upload.
  * The default value is null, which allows files with all mime types to be uploaded.
  * Each mime type specified can be a wildcard, e.g. image/*, or a specific mime type, e.g. image/png.
  * @returns Promise with response containing success message or error
  *
  * @example Update bucket
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .updateBucket('avatars', {
  *     public: false,
  *     allowedMimeTypes: ['image/png'],
  *     fileSizeLimit: 1024
  *   })
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "message": "Successfully updated"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: `select` and `update`
  *   - `objects` table permissions: none
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async updateBucket(id, options) {
    var _this4 = this;
    return _this4.handleOperation(async () => {
      return await put(_this4.fetch, `${_this4.url}/bucket/${id}`, {
        id,
        name: id,
        public: options.public,
        file_size_limit: options.fileSizeLimit,
        allowed_mime_types: options.allowedMimeTypes
      }, { headers: _this4.headers });
    });
  }
  /**
  * Removes all objects inside a single bucket.
  *
  * @category File Buckets
  * @param id The unique identifier of the bucket you would like to empty.
  * @returns Promise with success message or error
  *
  * @example Empty bucket
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .emptyBucket('avatars')
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "message": "Successfully emptied"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: `select`
  *   - `objects` table permissions: `select` and `delete`
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async emptyBucket(id) {
    var _this5 = this;
    return _this5.handleOperation(async () => {
      return await post(_this5.fetch, `${_this5.url}/bucket/${id}/empty`, {}, { headers: _this5.headers });
    });
  }
  /**
  * Deletes an existing bucket. A bucket can't be deleted with existing objects inside it.
  * You must first `empty()` the bucket.
  *
  * @category File Buckets
  * @param id The unique identifier of the bucket you would like to delete.
  * @returns Promise with success message or error
  *
  * @example Delete bucket
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .deleteBucket('avatars')
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "message": "Successfully deleted"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - RLS policy permissions required:
  *   - `buckets` table permissions: `select` and `delete`
  *   - `objects` table permissions: none
  * - Refer to the [Storage guide](/docs/guides/storage/security/access-control) on how access control works
  */
  async deleteBucket(id) {
    var _this6 = this;
    return _this6.handleOperation(async () => {
      return await remove(_this6.fetch, `${_this6.url}/bucket/${id}`, {}, { headers: _this6.headers });
    });
  }
  listBucketOptionsToQueryString(options) {
    const params = {};
    if (options) {
      if ("limit" in options) params.limit = String(options.limit);
      if ("offset" in options) params.offset = String(options.offset);
      if (options.search) params.search = options.search;
      if (options.sortColumn) params.sortColumn = options.sortColumn;
      if (options.sortOrder) params.sortOrder = options.sortOrder;
    }
    return Object.keys(params).length > 0 ? "?" + new URLSearchParams(params).toString() : "";
  }
};
var StorageAnalyticsClient = class extends BaseApiClient {
  /**
  * @alpha
  *
  * Creates a new StorageAnalyticsClient instance
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Analytics Buckets
  * @param url - The base URL for the storage API
  * @param headers - HTTP headers to include in requests
  * @param fetch - Optional custom fetch implementation
  *
  * @example Using supabase-js (recommended)
  * ```typescript
  * import { createClient } from '@supabase/supabase-js'
  *
  * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key')
  * const { data, error } = await supabase.storage.analytics.listBuckets()
  * ```
  *
  * @example Standalone import for bundle-sensitive environments
  * ```typescript
  * import { StorageAnalyticsClient } from '@supabase/storage-js'
  *
  * const client = new StorageAnalyticsClient(url, headers)
  * ```
  */
  constructor(url, headers = {}, fetch$1) {
    const finalUrl = url.replace(/\/$/, "");
    const finalHeaders = _objectSpread22(_objectSpread22({}, DEFAULT_HEADERS), headers);
    super(finalUrl, finalHeaders, fetch$1, "storage");
  }
  /**
  * @alpha
  *
  * Creates a new analytics bucket using Iceberg tables
  * Analytics buckets are optimized for analytical queries and data processing
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Analytics Buckets
  * @param name A unique name for the bucket you are creating
  * @returns Promise with response containing newly created analytics bucket or error
  *
  * @example Create analytics bucket
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .analytics
  *   .createBucket('analytics-data')
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "name": "analytics-data",
  *     "type": "ANALYTICS",
  *     "format": "iceberg",
  *     "created_at": "2024-05-22T22:26:05.100Z",
  *     "updated_at": "2024-05-22T22:26:05.100Z"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - Creates a new analytics bucket using Iceberg tables
  * - Analytics buckets are optimized for analytical queries and data processing
  */
  async createBucket(name) {
    var _this = this;
    return _this.handleOperation(async () => {
      return await post(_this.fetch, `${_this.url}/bucket`, { name }, { headers: _this.headers });
    });
  }
  /**
  * @alpha
  *
  * Retrieves the details of all Analytics Storage buckets within an existing project
  * Only returns buckets of type 'ANALYTICS'
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Analytics Buckets
  * @param options Query parameters for listing buckets
  * @param options.limit Maximum number of buckets to return
  * @param options.offset Number of buckets to skip
  * @param options.sortColumn Column to sort by ('name', 'created_at', 'updated_at')
  * @param options.sortOrder Sort order ('asc' or 'desc')
  * @param options.search Search term to filter bucket names
  * @returns Promise with response containing array of analytics buckets or error
  *
  * @example List analytics buckets
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .analytics
  *   .listBuckets({
  *     limit: 10,
  *     offset: 0,
  *     sortColumn: 'created_at',
  *     sortOrder: 'desc'
  *   })
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": [
  *     {
  *       "name": "analytics-data",
  *       "type": "ANALYTICS",
  *       "format": "iceberg",
  *       "created_at": "2024-05-22T22:26:05.100Z",
  *       "updated_at": "2024-05-22T22:26:05.100Z"
  *     }
  *   ],
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - Retrieves the details of all Analytics Storage buckets within an existing project
  * - Only returns buckets of type 'ANALYTICS'
  */
  async listBuckets(options) {
    var _this2 = this;
    return _this2.handleOperation(async () => {
      const queryParams = new URLSearchParams();
      if ((options === null || options === void 0 ? void 0 : options.limit) !== void 0) queryParams.set("limit", options.limit.toString());
      if ((options === null || options === void 0 ? void 0 : options.offset) !== void 0) queryParams.set("offset", options.offset.toString());
      if (options === null || options === void 0 ? void 0 : options.sortColumn) queryParams.set("sortColumn", options.sortColumn);
      if (options === null || options === void 0 ? void 0 : options.sortOrder) queryParams.set("sortOrder", options.sortOrder);
      if (options === null || options === void 0 ? void 0 : options.search) queryParams.set("search", options.search);
      const queryString = queryParams.toString();
      const url = queryString ? `${_this2.url}/bucket?${queryString}` : `${_this2.url}/bucket`;
      return await get(_this2.fetch, url, { headers: _this2.headers });
    });
  }
  /**
  * @alpha
  *
  * Deletes an existing analytics bucket
  * A bucket can't be deleted with existing objects inside it
  * You must first empty the bucket before deletion
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Analytics Buckets
  * @param bucketName The unique identifier of the bucket you would like to delete
  * @returns Promise with response containing success message or error
  *
  * @example Delete analytics bucket
  * ```js
  * const { data, error } = await supabase
  *   .storage
  *   .analytics
  *   .deleteBucket('analytics-data')
  * ```
  *
  * Response:
  * ```json
  * {
  *   "data": {
  *     "message": "Successfully deleted"
  *   },
  *   "error": null
  * }
  * ```
  *
  * @remarks
  * - Deletes an analytics bucket
  */
  async deleteBucket(bucketName) {
    var _this3 = this;
    return _this3.handleOperation(async () => {
      return await remove(_this3.fetch, `${_this3.url}/bucket/${bucketName}`, {}, { headers: _this3.headers });
    });
  }
  /**
  * @alpha
  *
  * Get an Iceberg REST Catalog client configured for a specific analytics bucket
  * Use this to perform advanced table and namespace operations within the bucket
  * The returned client provides full access to the Apache Iceberg REST Catalog API
  * with the Supabase `{ data, error }` pattern for consistent error handling on all operations.
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Analytics Buckets
  * @param bucketName - The name of the analytics bucket (warehouse) to connect to
  * @returns The wrapped Iceberg catalog client
  * @throws {StorageError} If the bucket name is invalid
  *
  * @example Get catalog and create table
  * ```js
  * // First, create an analytics bucket
  * const { data: bucket, error: bucketError } = await supabase
  *   .storage
  *   .analytics
  *   .createBucket('analytics-data')
  *
  * // Get the Iceberg catalog for that bucket
  * const catalog = supabase.storage.analytics.from('analytics-data')
  *
  * // Create a namespace
  * const { error: nsError } = await catalog.createNamespace({ namespace: ['default'] })
  *
  * // Create a table with schema
  * const { data: tableMetadata, error: tableError } = await catalog.createTable(
  *   { namespace: ['default'] },
  *   {
  *     name: 'events',
  *     schema: {
  *       type: 'struct',
  *       fields: [
  *         { id: 1, name: 'id', type: 'long', required: true },
  *         { id: 2, name: 'timestamp', type: 'timestamp', required: true },
  *         { id: 3, name: 'user_id', type: 'string', required: false }
  *       ],
  *       'schema-id': 0,
  *       'identifier-field-ids': [1]
  *     },
  *     'partition-spec': {
  *       'spec-id': 0,
  *       fields: []
  *     },
  *     'write-order': {
  *       'order-id': 0,
  *       fields: []
  *     },
  *     properties: {
  *       'write.format.default': 'parquet'
  *     }
  *   }
  * )
  * ```
  *
  * @example List tables in namespace
  * ```js
  * const catalog = supabase.storage.analytics.from('analytics-data')
  *
  * // List all tables in the default namespace
  * const { data: tables, error: listError } = await catalog.listTables({ namespace: ['default'] })
  * if (listError) {
  *   if (listError.isNotFound()) {
  *     console.log('Namespace not found')
  *   }
  *   return
  * }
  * console.log(tables) // [{ namespace: ['default'], name: 'events' }]
  * ```
  *
  * @example Working with namespaces
  * ```js
  * const catalog = supabase.storage.analytics.from('analytics-data')
  *
  * // List all namespaces
  * const { data: namespaces } = await catalog.listNamespaces()
  *
  * // Create namespace with properties
  * await catalog.createNamespace(
  *   { namespace: ['production'] },
  *   { properties: { owner: 'data-team', env: 'prod' } }
  * )
  * ```
  *
  * @example Cleanup operations
  * ```js
  * const catalog = supabase.storage.analytics.from('analytics-data')
  *
  * // Drop table with purge option (removes all data)
  * const { error: dropError } = await catalog.dropTable(
  *   { namespace: ['default'], name: 'events' },
  *   { purge: true }
  * )
  *
  * if (dropError?.isNotFound()) {
  *   console.log('Table does not exist')
  * }
  *
  * // Drop namespace (must be empty)
  * await catalog.dropNamespace({ namespace: ['default'] })
  * ```
  *
  * @remarks
  * This method provides a bridge between Supabase's bucket management and the standard
  * Apache Iceberg REST Catalog API. The bucket name maps to the Iceberg warehouse parameter.
  * All authentication and configuration is handled automatically using your Supabase credentials.
  *
  * **Error Handling**: Invalid bucket names throw immediately. All catalog
  * operations return `{ data, error }` where errors are `IcebergError` instances from iceberg-js.
  * Use helper methods like `error.isNotFound()` or check `error.status` for specific error handling.
  * Use `.throwOnError()` on the analytics client if you prefer exceptions for catalog operations.
  *
  * **Cleanup Operations**: When using `dropTable`, the `purge: true` option permanently
  * deletes all table data. Without it, the table is marked as deleted but data remains.
  *
  * **Library Dependency**: The returned catalog wraps `IcebergRestCatalog` from iceberg-js.
  * For complete API documentation and advanced usage, refer to the
  * [iceberg-js documentation](https://supabase.github.io/iceberg-js/).
  */
  from(bucketName) {
    var _this4 = this;
    if (!isValidBucketName(bucketName)) throw new StorageError("Invalid bucket name: File, folder, and bucket names must follow AWS object key naming guidelines and should avoid the use of any other characters.");
    const catalog = new IcebergRestCatalog({
      baseUrl: this.url,
      catalogName: bucketName,
      auth: {
        type: "custom",
        getHeaders: async () => _this4.headers
      },
      fetch: this.fetch
    });
    const shouldThrowOnError = this.shouldThrowOnError;
    return new Proxy(catalog, { get(target, prop) {
      const value = target[prop];
      if (typeof value !== "function") return value;
      return async (...args) => {
        try {
          return {
            data: await value.apply(target, args),
            error: null
          };
        } catch (error) {
          if (shouldThrowOnError) throw error;
          return {
            data: null,
            error
          };
        }
      };
    } });
  }
};
var VectorIndexApi = class extends BaseApiClient {
  /** Creates a new VectorIndexApi instance */
  constructor(url, headers = {}, fetch$1) {
    const finalUrl = url.replace(/\/$/, "");
    const finalHeaders = _objectSpread22(_objectSpread22({}, DEFAULT_HEADERS), {}, { "Content-Type": "application/json" }, headers);
    super(finalUrl, finalHeaders, fetch$1, "vectors");
  }
  /** Creates a new vector index within a bucket */
  async createIndex(options) {
    var _this = this;
    return _this.handleOperation(async () => {
      return await vectorsApi.post(_this.fetch, `${_this.url}/CreateIndex`, options, { headers: _this.headers }) || {};
    });
  }
  /** Retrieves metadata for a specific vector index */
  async getIndex(vectorBucketName, indexName) {
    var _this2 = this;
    return _this2.handleOperation(async () => {
      return await vectorsApi.post(_this2.fetch, `${_this2.url}/GetIndex`, {
        vectorBucketName,
        indexName
      }, { headers: _this2.headers });
    });
  }
  /** Lists vector indexes within a bucket with optional filtering and pagination */
  async listIndexes(options) {
    var _this3 = this;
    return _this3.handleOperation(async () => {
      return await vectorsApi.post(_this3.fetch, `${_this3.url}/ListIndexes`, options, { headers: _this3.headers });
    });
  }
  /** Deletes a vector index and all its data */
  async deleteIndex(vectorBucketName, indexName) {
    var _this4 = this;
    return _this4.handleOperation(async () => {
      return await vectorsApi.post(_this4.fetch, `${_this4.url}/DeleteIndex`, {
        vectorBucketName,
        indexName
      }, { headers: _this4.headers }) || {};
    });
  }
};
var VectorDataApi = class extends BaseApiClient {
  /** Creates a new VectorDataApi instance */
  constructor(url, headers = {}, fetch$1) {
    const finalUrl = url.replace(/\/$/, "");
    const finalHeaders = _objectSpread22(_objectSpread22({}, DEFAULT_HEADERS), {}, { "Content-Type": "application/json" }, headers);
    super(finalUrl, finalHeaders, fetch$1, "vectors");
  }
  /** Inserts or updates vectors in batch (1-500 per request) */
  async putVectors(options) {
    var _this = this;
    if (options.vectors.length < 1 || options.vectors.length > 500) throw new Error("Vector batch size must be between 1 and 500 items");
    return _this.handleOperation(async () => {
      return await vectorsApi.post(_this.fetch, `${_this.url}/PutVectors`, options, { headers: _this.headers }) || {};
    });
  }
  /** Retrieves vectors by their keys in batch */
  async getVectors(options) {
    var _this2 = this;
    return _this2.handleOperation(async () => {
      return await vectorsApi.post(_this2.fetch, `${_this2.url}/GetVectors`, options, { headers: _this2.headers });
    });
  }
  /** Lists vectors in an index with pagination */
  async listVectors(options) {
    var _this3 = this;
    if (options.segmentCount !== void 0) {
      if (options.segmentCount < 1 || options.segmentCount > 16) throw new Error("segmentCount must be between 1 and 16");
      if (options.segmentIndex !== void 0) {
        if (options.segmentIndex < 0 || options.segmentIndex >= options.segmentCount) throw new Error(`segmentIndex must be between 0 and ${options.segmentCount - 1}`);
      }
    }
    return _this3.handleOperation(async () => {
      return await vectorsApi.post(_this3.fetch, `${_this3.url}/ListVectors`, options, { headers: _this3.headers });
    });
  }
  /** Queries for similar vectors using approximate nearest neighbor search */
  async queryVectors(options) {
    var _this4 = this;
    return _this4.handleOperation(async () => {
      return await vectorsApi.post(_this4.fetch, `${_this4.url}/QueryVectors`, options, { headers: _this4.headers });
    });
  }
  /** Deletes vectors by their keys in batch (1-500 per request) */
  async deleteVectors(options) {
    var _this5 = this;
    if (options.keys.length < 1 || options.keys.length > 500) throw new Error("Keys batch size must be between 1 and 500 items");
    return _this5.handleOperation(async () => {
      return await vectorsApi.post(_this5.fetch, `${_this5.url}/DeleteVectors`, options, { headers: _this5.headers }) || {};
    });
  }
};
var VectorBucketApi = class extends BaseApiClient {
  /** Creates a new VectorBucketApi instance */
  constructor(url, headers = {}, fetch$1) {
    const finalUrl = url.replace(/\/$/, "");
    const finalHeaders = _objectSpread22(_objectSpread22({}, DEFAULT_HEADERS), {}, { "Content-Type": "application/json" }, headers);
    super(finalUrl, finalHeaders, fetch$1, "vectors");
  }
  /** Creates a new vector bucket */
  async createBucket(vectorBucketName) {
    var _this = this;
    return _this.handleOperation(async () => {
      return await vectorsApi.post(_this.fetch, `${_this.url}/CreateVectorBucket`, { vectorBucketName }, { headers: _this.headers }) || {};
    });
  }
  /** Retrieves metadata for a specific vector bucket */
  async getBucket(vectorBucketName) {
    var _this2 = this;
    return _this2.handleOperation(async () => {
      return await vectorsApi.post(_this2.fetch, `${_this2.url}/GetVectorBucket`, { vectorBucketName }, { headers: _this2.headers });
    });
  }
  /** Lists vector buckets with optional filtering and pagination */
  async listBuckets(options = {}) {
    var _this3 = this;
    return _this3.handleOperation(async () => {
      return await vectorsApi.post(_this3.fetch, `${_this3.url}/ListVectorBuckets`, options, { headers: _this3.headers });
    });
  }
  /** Deletes a vector bucket (must be empty first) */
  async deleteBucket(vectorBucketName) {
    var _this4 = this;
    return _this4.handleOperation(async () => {
      return await vectorsApi.post(_this4.fetch, `${_this4.url}/DeleteVectorBucket`, { vectorBucketName }, { headers: _this4.headers }) || {};
    });
  }
};
var StorageVectorsClient = class extends VectorBucketApi {
  /**
  * @alpha
  *
  * Creates a StorageVectorsClient that can manage buckets, indexes, and vectors.
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param url - Base URL of the Storage Vectors REST API.
  * @param options.headers - Optional headers (for example `Authorization`) applied to every request.
  * @param options.fetch - Optional custom `fetch` implementation for non-browser runtimes.
  *
  * @example Using supabase-js (recommended)
  * ```typescript
  * import { createClient } from '@supabase/supabase-js'
  *
  * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key')
  * const bucket = supabase.storage.vectors.from('embeddings-prod')
  * ```
  *
  * @example Standalone import for bundle-sensitive environments
  * ```typescript
  * import { StorageVectorsClient } from '@supabase/storage-js'
  *
  * const client = new StorageVectorsClient(url, options)
  * ```
  */
  constructor(url, options = {}) {
    super(url, options.headers || {}, options.fetch);
  }
  /**
  *
  * @alpha
  *
  * Access operations for a specific vector bucket
  * Returns a scoped client for index and vector operations within the bucket
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param vectorBucketName - Name of the vector bucket
  * @returns Bucket-scoped client with index and vector operations
  *
  * @example Accessing a vector bucket
  * ```typescript
  * const bucket = supabase.storage.vectors.from('embeddings-prod')
  * ```
  */
  from(vectorBucketName) {
    return new VectorBucketScope(this.url, this.headers, vectorBucketName, this.fetch);
  }
  /**
  *
  * @alpha
  *
  * Creates a new vector bucket
  * Vector buckets are containers for vector indexes and their data
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param vectorBucketName - Unique name for the vector bucket
  * @returns Promise with empty response on success or error
  *
  * @example Creating a vector bucket
  * ```typescript
  * const { data, error } = await supabase
  *   .storage
  *   .vectors
  *   .createBucket('embeddings-prod')
  * ```
  */
  async createBucket(vectorBucketName) {
    var _superprop_getCreateBucket = () => super.createBucket, _this = this;
    return _superprop_getCreateBucket().call(_this, vectorBucketName);
  }
  /**
  *
  * @alpha
  *
  * Retrieves metadata for a specific vector bucket
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param vectorBucketName - Name of the vector bucket
  * @returns Promise with bucket metadata or error
  *
  * @example Get bucket metadata
  * ```typescript
  * const { data, error } = await supabase
  *   .storage
  *   .vectors
  *   .getBucket('embeddings-prod')
  *
  * console.log('Bucket created:', data?.vectorBucket.creationTime)
  * ```
  */
  async getBucket(vectorBucketName) {
    var _superprop_getGetBucket = () => super.getBucket, _this2 = this;
    return _superprop_getGetBucket().call(_this2, vectorBucketName);
  }
  /**
  *
  * @alpha
  *
  * Lists all vector buckets with optional filtering and pagination
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param options - Optional filters (prefix, maxResults, nextToken)
  * @returns Promise with list of buckets or error
  *
  * @example List vector buckets
  * ```typescript
  * const { data, error } = await supabase
  *   .storage
  *   .vectors
  *   .listBuckets({ prefix: 'embeddings-' })
  *
  * data?.vectorBuckets.forEach(bucket => {
  *   console.log(bucket.vectorBucketName)
  * })
  * ```
  */
  async listBuckets(options = {}) {
    var _superprop_getListBuckets = () => super.listBuckets, _this3 = this;
    return _superprop_getListBuckets().call(_this3, options);
  }
  /**
  *
  * @alpha
  *
  * Deletes a vector bucket (bucket must be empty)
  * All indexes must be deleted before deleting the bucket
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param vectorBucketName - Name of the vector bucket to delete
  * @returns Promise with empty response on success or error
  *
  * @example Delete a vector bucket
  * ```typescript
  * const { data, error } = await supabase
  *   .storage
  *   .vectors
  *   .deleteBucket('embeddings-old')
  * ```
  */
  async deleteBucket(vectorBucketName) {
    var _superprop_getDeleteBucket = () => super.deleteBucket, _this4 = this;
    return _superprop_getDeleteBucket().call(_this4, vectorBucketName);
  }
};
var VectorBucketScope = class extends VectorIndexApi {
  /**
  * @alpha
  *
  * Creates a helper that automatically scopes all index operations to the provided bucket.
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @example Creating a vector bucket scope
  * ```typescript
  * const bucket = supabase.storage.vectors.from('embeddings-prod')
  * ```
  */
  constructor(url, headers, vectorBucketName, fetch$1) {
    super(url, headers, fetch$1);
    this.vectorBucketName = vectorBucketName;
  }
  /**
  *
  * @alpha
  *
  * Creates a new vector index in this bucket
  * Convenience method that automatically includes the bucket name
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param options - Index configuration (vectorBucketName is automatically set)
  * @returns Promise with empty response on success or error
  *
  * @example Creating a vector index
  * ```typescript
  * const bucket = supabase.storage.vectors.from('embeddings-prod')
  * await bucket.createIndex({
  *   indexName: 'documents-openai',
  *   dataType: 'float32',
  *   dimension: 1536,
  *   distanceMetric: 'cosine',
  *   metadataConfiguration: {
  *     nonFilterableMetadataKeys: ['raw_text']
  *   }
  * })
  * ```
  */
  async createIndex(options) {
    var _superprop_getCreateIndex = () => super.createIndex, _this5 = this;
    return _superprop_getCreateIndex().call(_this5, _objectSpread22(_objectSpread22({}, options), {}, { vectorBucketName: _this5.vectorBucketName }));
  }
  /**
  *
  * @alpha
  *
  * Lists indexes in this bucket
  * Convenience method that automatically includes the bucket name
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param options - Listing options (vectorBucketName is automatically set)
  * @returns Promise with response containing indexes array and pagination token or error
  *
  * @example List indexes
  * ```typescript
  * const bucket = supabase.storage.vectors.from('embeddings-prod')
  * const { data } = await bucket.listIndexes({ prefix: 'documents-' })
  * ```
  */
  async listIndexes(options = {}) {
    var _superprop_getListIndexes = () => super.listIndexes, _this6 = this;
    return _superprop_getListIndexes().call(_this6, _objectSpread22(_objectSpread22({}, options), {}, { vectorBucketName: _this6.vectorBucketName }));
  }
  /**
  *
  * @alpha
  *
  * Retrieves metadata for a specific index in this bucket
  * Convenience method that automatically includes the bucket name
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param indexName - Name of the index to retrieve
  * @returns Promise with index metadata or error
  *
  * @example Get index metadata
  * ```typescript
  * const bucket = supabase.storage.vectors.from('embeddings-prod')
  * const { data } = await bucket.getIndex('documents-openai')
  * console.log('Dimension:', data?.index.dimension)
  * ```
  */
  async getIndex(indexName) {
    var _superprop_getGetIndex = () => super.getIndex, _this7 = this;
    return _superprop_getGetIndex().call(_this7, _this7.vectorBucketName, indexName);
  }
  /**
  *
  * @alpha
  *
  * Deletes an index from this bucket
  * Convenience method that automatically includes the bucket name
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param indexName - Name of the index to delete
  * @returns Promise with empty response on success or error
  *
  * @example Delete an index
  * ```typescript
  * const bucket = supabase.storage.vectors.from('embeddings-prod')
  * await bucket.deleteIndex('old-index')
  * ```
  */
  async deleteIndex(indexName) {
    var _superprop_getDeleteIndex = () => super.deleteIndex, _this8 = this;
    return _superprop_getDeleteIndex().call(_this8, _this8.vectorBucketName, indexName);
  }
  /**
  *
  * @alpha
  *
  * Access operations for a specific index within this bucket
  * Returns a scoped client for vector data operations
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param indexName - Name of the index
  * @returns Index-scoped client with vector data operations
  *
  * @example Accessing an index
  * ```typescript
  * const index = supabase.storage.vectors.from('embeddings-prod').index('documents-openai')
  *
  * // Insert vectors
  * await index.putVectors({
  *   vectors: [
  *     { key: 'doc-1', data: { float32: [...] }, metadata: { title: 'Intro' } }
  *   ]
  * })
  *
  * // Query similar vectors
  * const { data } = await index.queryVectors({
  *   queryVector: { float32: [...] },
  *   topK: 5
  * })
  * ```
  */
  index(indexName) {
    return new VectorIndexScope(this.url, this.headers, this.vectorBucketName, indexName, this.fetch);
  }
};
var VectorIndexScope = class extends VectorDataApi {
  /**
  *
  * @alpha
  *
  * Creates a helper that automatically scopes all vector operations to the provided bucket/index names.
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @example Creating a vector index scope
  * ```typescript
  * const index = supabase.storage.vectors.from('embeddings-prod').index('documents-openai')
  * ```
  */
  constructor(url, headers, vectorBucketName, indexName, fetch$1) {
    super(url, headers, fetch$1);
    this.vectorBucketName = vectorBucketName;
    this.indexName = indexName;
  }
  /**
  *
  * @alpha
  *
  * Inserts or updates vectors in this index
  * Convenience method that automatically includes bucket and index names
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param options - Vector insertion options (bucket and index names automatically set)
  * @returns Promise with empty response on success or error
  *
  * @example Insert vectors into an index
  * ```typescript
  * const index = supabase.storage.vectors.from('embeddings-prod').index('documents-openai')
  * await index.putVectors({
  *   vectors: [
  *     {
  *       key: 'doc-1',
  *       data: { float32: [0.1, 0.2, ...] },
  *       metadata: { title: 'Introduction', page: 1 }
  *     }
  *   ]
  * })
  * ```
  */
  async putVectors(options) {
    var _superprop_getPutVectors = () => super.putVectors, _this9 = this;
    return _superprop_getPutVectors().call(_this9, _objectSpread22(_objectSpread22({}, options), {}, {
      vectorBucketName: _this9.vectorBucketName,
      indexName: _this9.indexName
    }));
  }
  /**
  *
  * @alpha
  *
  * Retrieves vectors by keys from this index
  * Convenience method that automatically includes bucket and index names
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param options - Vector retrieval options (bucket and index names automatically set)
  * @returns Promise with response containing vectors array or error
  *
  * @example Get vectors by keys
  * ```typescript
  * const index = supabase.storage.vectors.from('embeddings-prod').index('documents-openai')
  * const { data } = await index.getVectors({
  *   keys: ['doc-1', 'doc-2'],
  *   returnMetadata: true
  * })
  * ```
  */
  async getVectors(options) {
    var _superprop_getGetVectors = () => super.getVectors, _this10 = this;
    return _superprop_getGetVectors().call(_this10, _objectSpread22(_objectSpread22({}, options), {}, {
      vectorBucketName: _this10.vectorBucketName,
      indexName: _this10.indexName
    }));
  }
  /**
  *
  * @alpha
  *
  * Lists vectors in this index with pagination
  * Convenience method that automatically includes bucket and index names
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param options - Listing options (bucket and index names automatically set)
  * @returns Promise with response containing vectors array and pagination token or error
  *
  * @example List vectors with pagination
  * ```typescript
  * const index = supabase.storage.vectors.from('embeddings-prod').index('documents-openai')
  * const { data } = await index.listVectors({
  *   maxResults: 500,
  *   returnMetadata: true
  * })
  * ```
  */
  async listVectors(options = {}) {
    var _superprop_getListVectors = () => super.listVectors, _this11 = this;
    return _superprop_getListVectors().call(_this11, _objectSpread22(_objectSpread22({}, options), {}, {
      vectorBucketName: _this11.vectorBucketName,
      indexName: _this11.indexName
    }));
  }
  /**
  *
  * @alpha
  *
  * Queries for similar vectors in this index
  * Convenience method that automatically includes bucket and index names
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param options - Query options (bucket and index names automatically set)
  * @returns Promise with response containing matches array of similar vectors ordered by distance or error
  *
  * @example Query similar vectors
  * ```typescript
  * const index = supabase.storage.vectors.from('embeddings-prod').index('documents-openai')
  * const { data } = await index.queryVectors({
  *   queryVector: { float32: [0.1, 0.2, ...] },
  *   topK: 5,
  *   filter: { category: 'technical' },
  *   returnDistance: true,
  *   returnMetadata: true
  * })
  * ```
  */
  async queryVectors(options) {
    var _superprop_getQueryVectors = () => super.queryVectors, _this12 = this;
    return _superprop_getQueryVectors().call(_this12, _objectSpread22(_objectSpread22({}, options), {}, {
      vectorBucketName: _this12.vectorBucketName,
      indexName: _this12.indexName
    }));
  }
  /**
  *
  * @alpha
  *
  * Deletes vectors by keys from this index
  * Convenience method that automatically includes bucket and index names
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @param options - Deletion options (bucket and index names automatically set)
  * @returns Promise with empty response on success or error
  *
  * @example Delete vectors by keys
  * ```typescript
  * const index = supabase.storage.vectors.from('embeddings-prod').index('documents-openai')
  * await index.deleteVectors({
  *   keys: ['doc-1', 'doc-2', 'doc-3']
  * })
  * ```
  */
  async deleteVectors(options) {
    var _superprop_getDeleteVectors = () => super.deleteVectors, _this13 = this;
    return _superprop_getDeleteVectors().call(_this13, _objectSpread22(_objectSpread22({}, options), {}, {
      vectorBucketName: _this13.vectorBucketName,
      indexName: _this13.indexName
    }));
  }
};
var StorageClient = class extends StorageBucketApi {
  /**
  * Creates a client for Storage buckets, files, analytics, and vectors.
  *
  * @category File Buckets
  * @example Using supabase-js (recommended)
  * ```ts
  * import { createClient } from '@supabase/supabase-js'
  *
  * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key')
  * const avatars = supabase.storage.from('avatars')
  * ```
  *
  * @example Standalone import for bundle-sensitive environments
  * ```ts
  * import { StorageClient } from '@supabase/storage-js'
  *
  * const storage = new StorageClient('https://xyzcompany.supabase.co/storage/v1', {
  *   apikey: 'publishable-or-anon-key',
  * })
  * const avatars = storage.from('avatars')
  * ```
  */
  constructor(url, headers = {}, fetch$1, opts) {
    super(url, headers, fetch$1, opts);
  }
  /**
  * Perform file operation in a bucket.
  *
  * @category File Buckets
  * @param id The bucket id to operate on.
  *
  * @example Accessing a bucket
  * ```typescript
  * const avatars = supabase.storage.from('avatars')
  * ```
  */
  from(id) {
    return new StorageFileApi(this.url, this.headers, id, this.fetch);
  }
  /**
  *
  * @alpha
  *
  * Access vector storage operations.
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Vector Buckets
  * @returns A StorageVectorsClient instance configured with the current storage settings.
  */
  get vectors() {
    return new StorageVectorsClient(this.url + "/vector", {
      headers: this.headers,
      fetch: this.fetch
    });
  }
  /**
  *
  * @alpha
  *
  * Access analytics storage operations using Iceberg tables.
  *
  * **Public alpha:** This API is part of a public alpha release and may not be available to your account type.
  *
  * @category Analytics Buckets
  * @returns A StorageAnalyticsClient instance configured with the current storage settings.
  */
  get analytics() {
    return new StorageAnalyticsClient(this.url + "/iceberg", this.headers, this.fetch);
  }
};

// design/node_modules/@supabase/supabase-js/dist/index.mjs
var import_auth_js = __toESM(require_main3(), 1);
__reExport(dist_exports, __toESM(require_main2(), 1));
__reExport(dist_exports, __toESM(require_main3(), 1));
var version2 = "2.104.1";
var JS_ENV = "";
if (typeof Deno !== "undefined") JS_ENV = "deno";
else if (typeof document !== "undefined") JS_ENV = "web";
else if (typeof navigator !== "undefined" && navigator.product === "ReactNative") JS_ENV = "react-native";
else JS_ENV = "node";
var DEFAULT_HEADERS2 = { "X-Client-Info": `supabase-js-${JS_ENV}/${version2}` };
var DEFAULT_GLOBAL_OPTIONS = { headers: DEFAULT_HEADERS2 };
var DEFAULT_DB_OPTIONS = { schema: "public" };
var DEFAULT_AUTH_OPTIONS = {
  autoRefreshToken: true,
  persistSession: true,
  detectSessionInUrl: true,
  flowType: "implicit"
};
var DEFAULT_REALTIME_OPTIONS = {};
function _typeof3(o) {
  "@babel/helpers - typeof";
  return _typeof3 = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function(o$1) {
    return typeof o$1;
  } : function(o$1) {
    return o$1 && "function" == typeof Symbol && o$1.constructor === Symbol && o$1 !== Symbol.prototype ? "symbol" : typeof o$1;
  }, _typeof3(o);
}
function toPrimitive3(t, r) {
  if ("object" != _typeof3(t) || !t) return t;
  var e = t[Symbol.toPrimitive];
  if (void 0 !== e) {
    var i = e.call(t, r || "default");
    if ("object" != _typeof3(i)) return i;
    throw new TypeError("@@toPrimitive must return a primitive value.");
  }
  return ("string" === r ? String : Number)(t);
}
function toPropertyKey3(t) {
  var i = toPrimitive3(t, "string");
  return "symbol" == _typeof3(i) ? i : i + "";
}
function _defineProperty3(e, r, t) {
  return (r = toPropertyKey3(r)) in e ? Object.defineProperty(e, r, {
    value: t,
    enumerable: true,
    configurable: true,
    writable: true
  }) : e[r] = t, e;
}
function ownKeys4(e, r) {
  var t = Object.keys(e);
  if (Object.getOwnPropertySymbols) {
    var o = Object.getOwnPropertySymbols(e);
    r && (o = o.filter(function(r$1) {
      return Object.getOwnPropertyDescriptor(e, r$1).enumerable;
    })), t.push.apply(t, o);
  }
  return t;
}
function _objectSpread23(e) {
  for (var r = 1; r < arguments.length; r++) {
    var t = null != arguments[r] ? arguments[r] : {};
    r % 2 ? ownKeys4(Object(t), true).forEach(function(r$1) {
      _defineProperty3(e, r$1, t[r$1]);
    }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys4(Object(t)).forEach(function(r$1) {
      Object.defineProperty(e, r$1, Object.getOwnPropertyDescriptor(t, r$1));
    });
  }
  return e;
}
var resolveFetch2 = (customFetch) => {
  if (customFetch) return (...args) => customFetch(...args);
  return (...args) => fetch(...args);
};
var resolveHeadersConstructor = () => {
  return Headers;
};
var fetchWithAuth = (supabaseKey, getAccessToken, customFetch) => {
  const fetch$1 = resolveFetch2(customFetch);
  const HeadersConstructor = resolveHeadersConstructor();
  return async (input, init) => {
    var _await$getAccessToken;
    const accessToken = (_await$getAccessToken = await getAccessToken()) !== null && _await$getAccessToken !== void 0 ? _await$getAccessToken : supabaseKey;
    let headers = new HeadersConstructor(init === null || init === void 0 ? void 0 : init.headers);
    if (!headers.has("apikey")) headers.set("apikey", supabaseKey);
    if (!headers.has("Authorization")) headers.set("Authorization", `Bearer ${accessToken}`);
    return fetch$1(input, _objectSpread23(_objectSpread23({}, init), {}, { headers }));
  };
};
function ensureTrailingSlash(url) {
  return url.endsWith("/") ? url : url + "/";
}
function applySettingDefaults(options, defaults) {
  var _DEFAULT_GLOBAL_OPTIO, _globalOptions$header;
  const { db: dbOptions, auth: authOptions, realtime: realtimeOptions, global: globalOptions } = options;
  const { db: DEFAULT_DB_OPTIONS$1, auth: DEFAULT_AUTH_OPTIONS$1, realtime: DEFAULT_REALTIME_OPTIONS$1, global: DEFAULT_GLOBAL_OPTIONS$1 } = defaults;
  const result = {
    db: _objectSpread23(_objectSpread23({}, DEFAULT_DB_OPTIONS$1), dbOptions),
    auth: _objectSpread23(_objectSpread23({}, DEFAULT_AUTH_OPTIONS$1), authOptions),
    realtime: _objectSpread23(_objectSpread23({}, DEFAULT_REALTIME_OPTIONS$1), realtimeOptions),
    storage: {},
    global: _objectSpread23(_objectSpread23(_objectSpread23({}, DEFAULT_GLOBAL_OPTIONS$1), globalOptions), {}, { headers: _objectSpread23(_objectSpread23({}, (_DEFAULT_GLOBAL_OPTIO = DEFAULT_GLOBAL_OPTIONS$1 === null || DEFAULT_GLOBAL_OPTIONS$1 === void 0 ? void 0 : DEFAULT_GLOBAL_OPTIONS$1.headers) !== null && _DEFAULT_GLOBAL_OPTIO !== void 0 ? _DEFAULT_GLOBAL_OPTIO : {}), (_globalOptions$header = globalOptions === null || globalOptions === void 0 ? void 0 : globalOptions.headers) !== null && _globalOptions$header !== void 0 ? _globalOptions$header : {}) }),
    accessToken: async () => ""
  };
  if (options.accessToken) result.accessToken = options.accessToken;
  else delete result.accessToken;
  return result;
}
function validateSupabaseUrl(supabaseUrl) {
  const trimmedUrl = supabaseUrl === null || supabaseUrl === void 0 ? void 0 : supabaseUrl.trim();
  if (!trimmedUrl) throw new Error("supabaseUrl is required.");
  if (!trimmedUrl.match(/^https?:\/\//i)) throw new Error("Invalid supabaseUrl: Must be a valid HTTP or HTTPS URL.");
  try {
    return new URL(ensureTrailingSlash(trimmedUrl));
  } catch (_unused) {
    throw Error("Invalid supabaseUrl: Provided URL is malformed.");
  }
}
var SupabaseAuthClient = class extends import_auth_js.AuthClient {
  constructor(options) {
    super(options);
  }
};
var SupabaseClient = class {
  /**
  * Create a new client for use in the browser.
  *
  * @category Initializing
  *
  * @param supabaseUrl The unique Supabase URL which is supplied when you create a new project in your project dashboard.
  * @param supabaseKey The unique Supabase Key which is supplied when you create a new project in your project dashboard.
  * @param options.db.schema You can switch in between schemas. The schema needs to be on the list of exposed schemas inside Supabase.
  * @param options.auth.autoRefreshToken Set to "true" if you want to automatically refresh the token before expiring.
  * @param options.auth.persistSession Set to "true" if you want to automatically save the user session into local storage.
  * @param options.auth.detectSessionInUrl Set to "true" if you want to automatically detects OAuth grants in the URL and signs in the user.
  * @param options.realtime Options passed along to realtime-js constructor.
  * @param options.storage Options passed along to the storage-js constructor.
  * @param options.global.fetch A custom fetch implementation.
  * @param options.global.headers Any additional headers to send with each network request.
  *
  * @example Creating a client
  * ```js
  * import { createClient } from '@supabase/supabase-js'
  *
  * // Create a single supabase client for interacting with your database
  * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key')
  * ```
  *
  * @example With a custom domain
  * ```js
  * import { createClient } from '@supabase/supabase-js'
  *
  * // Use a custom domain as the supabase URL
  * const supabase = createClient('https://my-custom-domain.com', 'publishable-or-anon-key')
  * ```
  *
  * @example With additional parameters
  * ```js
  * import { createClient } from '@supabase/supabase-js'
  *
  * const options = {
  *   db: {
  *     schema: 'public',
  *   },
  *   auth: {
  *     autoRefreshToken: true,
  *     persistSession: true,
  *     detectSessionInUrl: true
  *   },
  *   global: {
  *     headers: { 'x-my-custom-header': 'my-app-name' },
  *   },
  * }
  * const supabase = createClient("https://xyzcompany.supabase.co", "publishable-or-anon-key", options)
  * ```
  *
  * @exampleDescription With custom schemas
  * By default the API server points to the `public` schema. You can enable other database schemas within the Dashboard.
  * Go to [Settings > API > Exposed schemas](/dashboard/project/_/settings/api) and add the schema which you want to expose to the API.
  *
  * Note: each client connection can only access a single schema, so the code above can access the `other_schema` schema but cannot access the `public` schema.
  *
  * @example With custom schemas
  * ```js
  * import { createClient } from '@supabase/supabase-js'
  *
  * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key', {
  *   // Provide a custom schema. Defaults to "public".
  *   db: { schema: 'other_schema' }
  * })
  * ```
  *
  * @exampleDescription Custom fetch implementation
  * `supabase-js` uses the [`cross-fetch`](https://www.npmjs.com/package/cross-fetch) library to make HTTP requests,
  * but an alternative `fetch` implementation can be provided as an option.
  * This is most useful in environments where `cross-fetch` is not compatible (for instance Cloudflare Workers).
  *
  * @example Custom fetch implementation
  * ```js
  * import { createClient } from '@supabase/supabase-js'
  *
  * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key', {
  *   global: { fetch: fetch.bind(globalThis) }
  * })
  * ```
  *
  * @exampleDescription React Native options with AsyncStorage
  * For React Native we recommend using `AsyncStorage` as the storage implementation for Supabase Auth.
  *
  * @example React Native options with AsyncStorage
  * ```js
  * import 'react-native-url-polyfill/auto'
  * import { createClient } from '@supabase/supabase-js'
  * import AsyncStorage from "@react-native-async-storage/async-storage";
  *
  * const supabase = createClient("https://xyzcompany.supabase.co", "publishable-or-anon-key", {
  *   auth: {
  *     storage: AsyncStorage,
  *     autoRefreshToken: true,
  *     persistSession: true,
  *     detectSessionInUrl: false,
  *   },
  * });
  * ```
  *
  * @exampleDescription React Native options with Expo SecureStore
  * If you wish to encrypt the user's session information, you can use `aes-js` and store the encryption key in Expo SecureStore.
  * The `aes-js` library, a reputable JavaScript-only implementation of the AES encryption algorithm in CTR mode.
  * A new 256-bit encryption key is generated using the `react-native-get-random-values` library.
  * This key is stored inside Expo's SecureStore, while the value is encrypted and placed inside AsyncStorage.
  *
  * Please make sure that:
  * - You keep the `expo-secure-store`, `aes-js` and `react-native-get-random-values` libraries up-to-date.
  * - Choose the correct [`SecureStoreOptions`](https://docs.expo.dev/versions/latest/sdk/securestore/#securestoreoptions) for your app's needs.
  *   E.g. [`SecureStore.WHEN_UNLOCKED`](https://docs.expo.dev/versions/latest/sdk/securestore/#securestorewhen_unlocked) regulates when the data can be accessed.
  * - Carefully consider optimizations or other modifications to the above example, as those can lead to introducing subtle security vulnerabilities.
  *
  * @example React Native options with Expo SecureStore
  * ```ts
  * import 'react-native-url-polyfill/auto'
  * import { createClient } from '@supabase/supabase-js'
  * import AsyncStorage from '@react-native-async-storage/async-storage';
  * import * as SecureStore from 'expo-secure-store';
  * import * as aesjs from 'aes-js';
  * import 'react-native-get-random-values';
  *
  * // As Expo's SecureStore does not support values larger than 2048
  * // bytes, an AES-256 key is generated and stored in SecureStore, while
  * // it is used to encrypt/decrypt values stored in AsyncStorage.
  * class LargeSecureStore {
  *   private async _encrypt(key: string, value: string) {
  *     const encryptionKey = crypto.getRandomValues(new Uint8Array(256 / 8));
  *
  *     const cipher = new aesjs.ModeOfOperation.ctr(encryptionKey, new aesjs.Counter(1));
  *     const encryptedBytes = cipher.encrypt(aesjs.utils.utf8.toBytes(value));
  *
  *     await SecureStore.setItemAsync(key, aesjs.utils.hex.fromBytes(encryptionKey));
  *
  *     return aesjs.utils.hex.fromBytes(encryptedBytes);
  *   }
  *
  *   private async _decrypt(key: string, value: string) {
  *     const encryptionKeyHex = await SecureStore.getItemAsync(key);
  *     if (!encryptionKeyHex) {
  *       return encryptionKeyHex;
  *     }
  *
  *     const cipher = new aesjs.ModeOfOperation.ctr(aesjs.utils.hex.toBytes(encryptionKeyHex), new aesjs.Counter(1));
  *     const decryptedBytes = cipher.decrypt(aesjs.utils.hex.toBytes(value));
  *
  *     return aesjs.utils.utf8.fromBytes(decryptedBytes);
  *   }
  *
  *   async getItem(key: string) {
  *     const encrypted = await AsyncStorage.getItem(key);
  *     if (!encrypted) { return encrypted; }
  *
  *     return await this._decrypt(key, encrypted);
  *   }
  *
  *   async removeItem(key: string) {
  *     await AsyncStorage.removeItem(key);
  *     await SecureStore.deleteItemAsync(key);
  *   }
  *
  *   async setItem(key: string, value: string) {
  *     const encrypted = await this._encrypt(key, value);
  *
  *     await AsyncStorage.setItem(key, encrypted);
  *   }
  * }
  *
  * const supabase = createClient("https://xyzcompany.supabase.co", "publishable-or-anon-key", {
  *   auth: {
  *     storage: new LargeSecureStore(),
  *     autoRefreshToken: true,
  *     persistSession: true,
  *     detectSessionInUrl: false,
  *   },
  * });
  * ```
  *
  * @example With a database query
  * ```ts
  * import { createClient } from '@supabase/supabase-js'
  *
  * const supabase = createClient('https://xyzcompany.supabase.co', 'publishable-or-anon-key')
  *
  * const { data } = await supabase.from('profiles').select('*')
  * ```
  */
  constructor(supabaseUrl, supabaseKey, options) {
    var _settings$auth$storag, _settings$global$head;
    this.supabaseUrl = supabaseUrl;
    this.supabaseKey = supabaseKey;
    const baseUrl = validateSupabaseUrl(supabaseUrl);
    if (!supabaseKey) throw new Error("supabaseKey is required.");
    this.realtimeUrl = new URL("realtime/v1", baseUrl);
    this.realtimeUrl.protocol = this.realtimeUrl.protocol.replace("http", "ws");
    this.authUrl = new URL("auth/v1", baseUrl);
    this.storageUrl = new URL("storage/v1", baseUrl);
    this.functionsUrl = new URL("functions/v1", baseUrl);
    const defaultStorageKey = `sb-${baseUrl.hostname.split(".")[0]}-auth-token`;
    const DEFAULTS = {
      db: DEFAULT_DB_OPTIONS,
      realtime: DEFAULT_REALTIME_OPTIONS,
      auth: _objectSpread23(_objectSpread23({}, DEFAULT_AUTH_OPTIONS), {}, { storageKey: defaultStorageKey }),
      global: DEFAULT_GLOBAL_OPTIONS
    };
    const settings = applySettingDefaults(options !== null && options !== void 0 ? options : {}, DEFAULTS);
    this.storageKey = (_settings$auth$storag = settings.auth.storageKey) !== null && _settings$auth$storag !== void 0 ? _settings$auth$storag : "";
    this.headers = (_settings$global$head = settings.global.headers) !== null && _settings$global$head !== void 0 ? _settings$global$head : {};
    if (!settings.accessToken) {
      var _settings$auth;
      this.auth = this._initSupabaseAuthClient((_settings$auth = settings.auth) !== null && _settings$auth !== void 0 ? _settings$auth : {}, this.headers, settings.global.fetch);
    } else {
      this.accessToken = settings.accessToken;
      this.auth = new Proxy({}, { get: (_, prop) => {
        throw new Error(`@supabase/supabase-js: Supabase Client is configured with the accessToken option, accessing supabase.auth.${String(prop)} is not possible`);
      } });
    }
    this.fetch = fetchWithAuth(supabaseKey, this._getAccessToken.bind(this), settings.global.fetch);
    this.realtime = this._initRealtimeClient(_objectSpread23({
      headers: this.headers,
      accessToken: this._getAccessToken.bind(this),
      fetch: this.fetch
    }, settings.realtime));
    if (this.accessToken) Promise.resolve(this.accessToken()).then((token) => this.realtime.setAuth(token)).catch((e) => console.warn("Failed to set initial Realtime auth token:", e));
    this.rest = new PostgrestClient(new URL("rest/v1", baseUrl).href, {
      headers: this.headers,
      schema: settings.db.schema,
      fetch: this.fetch,
      timeout: settings.db.timeout,
      urlLengthLimit: settings.db.urlLengthLimit
    });
    this.storage = new StorageClient(this.storageUrl.href, this.headers, this.fetch, options === null || options === void 0 ? void 0 : options.storage);
    if (!settings.accessToken) this._listenForAuthEvents();
  }
  /**
  * Supabase Functions allows you to deploy and invoke edge functions.
  */
  get functions() {
    return new import_functions_js.FunctionsClient(this.functionsUrl.href, {
      headers: this.headers,
      customFetch: this.fetch
    });
  }
  /**
  * Perform a query on a table or a view.
  *
  * @param relation - The table or view name to query
  */
  from(relation) {
    return this.rest.from(relation);
  }
  /**
  * Select a schema to query or perform an function (rpc) call.
  *
  * The schema needs to be on the list of exposed schemas inside Supabase.
  *
  * @param schema - The schema to query
  */
  schema(schema) {
    return this.rest.schema(schema);
  }
  /**
  * Perform a function call.
  *
  * @param fn - The function name to call
  * @param args - The arguments to pass to the function call
  * @param options - Named parameters
  * @param options.head - When set to `true`, `data` will not be returned.
  * Useful if you only need the count.
  * @param options.get - When set to `true`, the function will be called with
  * read-only access mode.
  * @param options.count - Count algorithm to use to count rows returned by the
  * function. Only applicable for [set-returning
  * functions](https://www.postgresql.org/docs/current/functions-srf.html).
  *
  * `"exact"`: Exact but slow count algorithm. Performs a `COUNT(*)` under the
  * hood.
  *
  * `"planned"`: Approximated but fast count algorithm. Uses the Postgres
  * statistics under the hood.
  *
  * `"estimated"`: Uses exact count for low numbers and planned count for high
  * numbers.
  */
  rpc(fn, args = {}, options = {
    head: false,
    get: false,
    count: void 0
  }) {
    return this.rest.rpc(fn, args, options);
  }
  /**
  * Creates a Realtime channel with Broadcast, Presence, and Postgres Changes.
  *
  * @param {string} name - The name of the Realtime channel.
  * @param {Object} opts - The options to pass to the Realtime channel.
  *
  */
  channel(name, opts = { config: {} }) {
    return this.realtime.channel(name, opts);
  }
  /**
  * Returns all Realtime channels.
  *
  * @category Initializing
  *
  * @example Get all channels
  * ```js
  * const channels = supabase.getChannels()
  * ```
  */
  getChannels() {
    return this.realtime.getChannels();
  }
  /**
  * Unsubscribes and removes Realtime channel from Realtime client.
  *
  * @param {RealtimeChannel} channel - The name of the Realtime channel.
  *
  *
  * @category Initializing
  *
  * @remarks
  * - Removing a channel is a great way to maintain the performance of your project's Realtime service as well as your database if you're listening to Postgres changes. Supabase will automatically handle cleanup 30 seconds after a client is disconnected, but unused channels may cause degradation as more clients are simultaneously subscribed.
  *
  * @example Removes a channel
  * ```js
  * supabase.removeChannel(myChannel)
  * ```
  */
  removeChannel(channel) {
    return this.realtime.removeChannel(channel);
  }
  /**
  * Unsubscribes and removes all Realtime channels from Realtime client.
  *
  * @category Initializing
  *
  * @remarks
  * - Removing channels is a great way to maintain the performance of your project's Realtime service as well as your database if you're listening to Postgres changes. Supabase will automatically handle cleanup 30 seconds after a client is disconnected, but unused channels may cause degradation as more clients are simultaneously subscribed.
  *
  * @example Remove all channels
  * ```js
  * supabase.removeAllChannels()
  * ```
  */
  removeAllChannels() {
    return this.realtime.removeAllChannels();
  }
  async _getAccessToken() {
    var _this = this;
    var _data$session$access_, _data$session;
    if (_this.accessToken) return await _this.accessToken();
    const { data } = await _this.auth.getSession();
    return (_data$session$access_ = (_data$session = data.session) === null || _data$session === void 0 ? void 0 : _data$session.access_token) !== null && _data$session$access_ !== void 0 ? _data$session$access_ : _this.supabaseKey;
  }
  _initSupabaseAuthClient({ autoRefreshToken, persistSession, detectSessionInUrl, storage, userStorage, storageKey, flowType, lock, debug, throwOnError }, headers, fetch$1) {
    const authHeaders = {
      Authorization: `Bearer ${this.supabaseKey}`,
      apikey: `${this.supabaseKey}`
    };
    return new SupabaseAuthClient({
      url: this.authUrl.href,
      headers: _objectSpread23(_objectSpread23({}, authHeaders), headers),
      storageKey,
      autoRefreshToken,
      persistSession,
      detectSessionInUrl,
      storage,
      userStorage,
      flowType,
      lock,
      debug,
      throwOnError,
      fetch: fetch$1,
      hasCustomAuthorizationHeader: Object.keys(this.headers).some((key) => key.toLowerCase() === "authorization")
    });
  }
  _initRealtimeClient(options) {
    return new import_realtime_js.RealtimeClient(this.realtimeUrl.href, _objectSpread23(_objectSpread23({}, options), {}, { params: _objectSpread23(_objectSpread23({}, { apikey: this.supabaseKey }), options === null || options === void 0 ? void 0 : options.params) }));
  }
  _listenForAuthEvents() {
    return this.auth.onAuthStateChange((event, session) => {
      this._handleTokenChanged(event, "CLIENT", session === null || session === void 0 ? void 0 : session.access_token);
    });
  }
  _handleTokenChanged(event, source, token) {
    if ((event === "TOKEN_REFRESHED" || event === "SIGNED_IN") && this.changedAccessToken !== token) {
      this.changedAccessToken = token;
      this.realtime.setAuth(token);
    } else if (event === "SIGNED_OUT") {
      this.realtime.setAuth();
      if (source == "STORAGE") this.auth.signOut();
      this.changedAccessToken = void 0;
    }
  }
};
var createClient = (supabaseUrl, supabaseKey, options) => {
  return new SupabaseClient(supabaseUrl, supabaseKey, options);
};
function shouldShowDeprecationWarning() {
  if (typeof window !== "undefined") return false;
  const _process = globalThis["process"];
  if (!_process) return false;
  const processVersion = _process["version"];
  if (processVersion === void 0 || processVersion === null) return false;
  const versionMatch = processVersion.match(/^v(\d+)\./);
  if (!versionMatch) return false;
  return parseInt(versionMatch[1], 10) <= 18;
}
if (shouldShowDeprecationWarning()) console.warn("\u26A0\uFE0F  Node.js 18 and below are deprecated and will no longer be supported in future versions of @supabase/supabase-js. Please upgrade to Node.js 20 or later. For more information, visit: https://github.com/orgs/supabase/discussions/37217");

// design/netlify/functions/api.ts
var env = {
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
  tiktokClientSecret: process.env.PLATFORM_TIKTOK_CLIENT_SECRET || ""
};
function response(statusCode, body, headers = {}) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      ...headers
    },
    body: JSON.stringify(body)
  };
}
function redirect(location2) {
  return {
    statusCode: 302,
    headers: {
      Location: location2,
      "Cache-Control": "no-store"
    },
    body: ""
  };
}
function oauthRedirect(location2) {
  return response(200, { redirect: location2 });
}
function compactNumber(value) {
  const safe = Number(value || 0);
  if (safe >= 1e6) return `${(safe / 1e6).toFixed(1)}M`;
  if (safe >= 1e3) return `${(safe / 1e3).toFixed(1)}K`;
  return String(Math.round(safe));
}
function slugify(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 50);
}
function parseBody(event) {
  if (!event.body) return {};
  try {
    return JSON.parse(event.body);
  } catch {
    return {};
  }
}
function getPath(event) {
  return event.path.replace(/^\/\.netlify\/functions\/api/, "").replace(/^\/api/, "") || "/";
}
function queryValue(event, key) {
  if (event.queryStringParameters?.[key]) return event.queryStringParameters[key] || "";
  const raw = event.rawQuery || "";
  const params = new URLSearchParams(raw.startsWith("?") ? raw.slice(1) : raw);
  return params.get(key) || "";
}
function createPublicClient() {
  return createClient(env.supabaseUrl, env.supabaseAnonKey, {
    auth: { persistSession: false, autoRefreshToken: false }
  });
}
function createAdminClient() {
  return createClient(env.supabaseUrl, env.supabaseServiceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false }
  });
}
function normalizeUsername(value) {
  return value.trim().toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 32);
}
function isEmail(value) {
  return /\S+@\S+\.\S+/.test(value);
}
function internalEmailForUsername(username) {
  return `${normalizeUsername(username)}@users.local`;
}
async function resolveIdentifierToEmail(admin, identifier) {
  const trimmed = String(identifier || "").trim().toLowerCase();
  if (!trimmed) return "";
  if (isEmail(trimmed)) return trimmed;
  const normalized = normalizeUsername(trimmed);
  const { data: profiles } = await admin.from("profiles").select("email, username").limit(500);
  const match = (profiles || []).find((profile) => {
    const username = String(profile.username || "").trim().toLowerCase();
    const email = String(profile.email || "").trim().toLowerCase();
    return username === normalized || email === trimmed || email.startsWith(`${trimmed}@`);
  });
  if (match?.email) return String(match.email).trim().toLowerCase();
  return internalEmailForUsername(trimmed);
}
async function handleAuthSignIn(event, admin) {
  const body = parseBody(event);
  const identifier = String(body.identifier || body.username || body.email || "").trim();
  const password = String(body.password || "");
  if (!identifier || !password) {
    return response(400, { error: "Vui l\xF2ng nh\u1EADp \u0111\u1EA7y \u0111\u1EE7 t\xEAn \u0111\u0103ng nh\u1EADp v\xE0 m\u1EADt kh\u1EA9u." });
  }
  const email = await resolveIdentifierToEmail(admin, identifier);
  const client = createPublicClient();
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  if (error || !data.session || !data.user) {
    return response(401, { error: "Sai t\xEAn \u0111\u0103ng nh\u1EADp ho\u1EB7c m\u1EADt kh\u1EA9u." });
  }
  await ensureWorkspaceForUser(admin, data.user);
  return response(200, {
    session: {
      access_token: data.session.access_token,
      refresh_token: data.session.refresh_token,
      expires_at: data.session.expires_at,
      expires_in: data.session.expires_in,
      token_type: data.session.token_type,
      user: data.user
    }
  });
}
async function handleAuthSignUp(event, admin) {
  const body = parseBody(event);
  const name = String(body.name || "").trim();
  const username = normalizeUsername(String(body.username || ""));
  const password = String(body.password || "");
  const email = String(body.email || "").trim().toLowerCase() || internalEmailForUsername(username);
  if (!name || !username || !password) {
    return response(400, { error: "Vui l\xF2ng nh\u1EADp \u0111\u1EA7y \u0111\u1EE7 h\u1ECD t\xEAn, t\xEAn \u0111\u0103ng nh\u1EADp v\xE0 m\u1EADt kh\u1EA9u." });
  }
  const { data: existingProfiles } = await admin.from("profiles").select("email, username").limit(500);
  const duplicated = (existingProfiles || []).find((profile) => {
    const existingUsername = String(profile.username || "").trim().toLowerCase();
    const existingEmail = String(profile.email || "").trim().toLowerCase();
    return existingUsername === username || existingEmail === email;
  });
  if (duplicated) {
    return response(400, { error: "T\xEAn \u0111\u0103ng nh\u1EADp ho\u1EB7c email \u0111\xE3 t\u1ED3n t\u1EA1i." });
  }
  const created = await admin.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
    user_metadata: {
      full_name: name,
      username
    }
  });
  if (created.error || !created.data.user) {
    return response(400, { error: created.error?.message || "Kh\xF4ng th\u1EC3 t\u1EA1o t\xE0i kho\u1EA3n." });
  }
  await admin.from("profiles").upsert({ id: created.data.user.id, email, full_name: name, username }, { onConflict: "id" });
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
      user: signedIn.data.user
    }
  });
}
async function getCurrentUser(event) {
  const authorization = event.headers.authorization || event.headers.Authorization;
  if (!authorization || !authorization.startsWith("Bearer ")) {
    return null;
  }
  const client = createClient(env.supabaseUrl, env.supabaseAnonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { headers: { Authorization: authorization } }
  });
  const { data, error } = await client.auth.getUser();
  if (error || !data.user) return null;
  return data.user;
}
function signedState(payload) {
  const data = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = import_node_crypto.default.createHmac("sha256", env.appStateSecret).update(data).digest("base64url");
  return `${data}.${signature}`;
}
function verifyState(value) {
  const [data, signature] = value.split(".");
  if (!data || !signature) throw new Error("Invalid state");
  const expected = import_node_crypto.default.createHmac("sha256", env.appStateSecret).update(data).digest("base64url");
  if (signature !== expected) throw new Error("Invalid state signature");
  const payload = JSON.parse(Buffer.from(data, "base64url").toString("utf8"));
  if (!payload.ts || Date.now() - Number(payload.ts) > 10 * 60 * 1e3) {
    throw new Error("Expired state");
  }
  return payload;
}
async function ensureWorkspaceForUser(admin, user) {
  const { data: membershipRows, error: membershipError } = await admin.from("workspace_members").select("id, role, workspace:workspaces(id, name, slug)").eq("user_id", user.id).limit(1);
  if (membershipError) throw membershipError;
  if (membershipRows && membershipRows.length > 0) {
    const row = membershipRows[0];
    return {
      workspace: row.workspace,
      membership: { id: row.id, role: row.role }
    };
  }
  const baseName = user.user_metadata?.workspace_name || user.user_metadata?.full_name || user.email?.split("@")[0] || "Workspace";
  const workspaceName = `${baseName} Workspace`;
  const slugBase = slugify(workspaceName) || "workspace";
  const { data: workspace, error: workspaceError } = await admin.from("workspaces").insert({
    name: workspaceName,
    slug: `${slugBase}-${import_node_crypto.default.randomBytes(3).toString("hex")}`,
    owner_user_id: user.id
  }).select("id, name, slug").single();
  if (workspaceError || !workspace) throw workspaceError || new Error("Failed to create workspace");
  const { data: membership, error: createMembershipError } = await admin.from("workspace_members").insert({
    workspace_id: workspace.id,
    user_id: user.id,
    role: "owner"
  }).select("id, role").single();
  if (createMembershipError || !membership) throw createMembershipError || new Error("Failed to create workspace membership");
  await admin.from("channel_groups").insert([
    { workspace_id: workspace.id, name: "T\u1EA5t c\u1EA3 k\xEAnh", position: 0, is_favorite: true },
    { workspace_id: workspace.id, name: "Th\u01B0\u01A1ng hi\u1EC7u", position: 1 },
    { workspace_id: workspace.id, name: "Campaign", position: 2 }
  ]);
  await admin.from("user_settings").upsert({ user_id: user.id });
  return {
    workspace,
    membership
  };
}
async function getWorkspaceMembership(admin, workspaceId, userId) {
  const { data, error } = await admin.from("workspace_members").select("id, role, workspace:workspaces(id, name, slug)").eq("workspace_id", workspaceId).eq("user_id", userId).single();
  if (error || !data) return null;
  return data;
}
async function fetchJson(url, init) {
  const response2 = await fetch(url, init);
  const json = await response2.json().catch(() => ({}));
  if (!response2.ok) {
    throw new Error(json.error?.message || json.error_description || `Request failed: ${response2.status}`);
  }
  return json;
}
async function upsertAccount(admin, account) {
  const { data, error } = await admin.from("social_accounts").upsert(
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
      metadata: account.metadata || {}
    },
    { onConflict: "workspace_id,platform,account_platform_id" }
  ).select("*").single();
  if (error || !data) throw error || new Error("Failed to upsert account");
  return data;
}
async function saveTokens(admin, socialAccountId, tokens) {
  const tokenExpiresAt = tokens.expiresIn && Number(tokens.expiresIn) > 0 ? new Date(Date.now() + Number(tokens.expiresIn) * 1e3).toISOString() : null;
  const { error } = await admin.from("social_account_tokens").upsert({
    social_account_id: socialAccountId,
    access_token: tokens.accessToken,
    refresh_token: tokens.refreshToken || "",
    token_expires_at: tokenExpiresAt,
    scope: tokens.scope || "",
    token_metadata: tokens.metadata || {}
  });
  if (error) throw error;
}
async function getTokens(admin, socialAccountId) {
  const { data, error } = await admin.from("social_account_tokens").select("*").eq("social_account_id", socialAccountId).single();
  if (error || !data) throw error || new Error("Missing token");
  return data;
}
function tokenExpiresSoon(token) {
  if (!token?.token_expires_at) return false;
  return new Date(token.token_expires_at).getTime() <= Date.now() + 5 * 60 * 1e3;
}
function tokenExpiresWithin(token, ms) {
  if (!token?.token_expires_at) return false;
  return new Date(token.token_expires_at).getTime() <= Date.now() + ms;
}
function isReconnectError(message) {
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
    "reconnect"
  ].some((part) => value.includes(part));
}
function describeTokenHealth(account, token) {
  const expiresAt = token?.token_expires_at || null;
  const hasRefreshToken = Boolean(token?.refresh_token);
  const reconnectRequired = account.connection_status !== "connected" || isReconnectError(account.last_error || "");
  if (!token?.access_token) {
    return {
      status: "missing",
      label: "Thi\u1EBFu token",
      severity: "error",
      reconnectRequired: true,
      hasRefreshToken,
      expiresAt,
      description: "K\xEAnh ch\u01B0a c\xF3 access token h\u1EE3p l\u1EC7."
    };
  }
  if (expiresAt && new Date(expiresAt).getTime() <= Date.now()) {
    return {
      status: hasRefreshToken ? "expired_refreshable" : "expired",
      label: hasRefreshToken ? "\u0110\xE3 h\u1EBFt h\u1EA1n, c\xF3 th\u1EC3 t\u1EF1 l\xE0m m\u1EDBi" : "\u0110\xE3 h\u1EBFt h\u1EA1n",
      severity: hasRefreshToken ? "warning" : "error",
      reconnectRequired: !hasRefreshToken || reconnectRequired,
      hasRefreshToken,
      expiresAt,
      description: hasRefreshToken ? "H\u1EC7 th\u1ED1ng s\u1EBD th\u1EED t\u1EF1 l\xE0m m\u1EDBi token \u1EDF l\u1EA7n \u0111\u1ED3ng b\u1ED9 k\u1EBF ti\u1EBFp." : "Token \u0111\xE3 h\u1EBFt h\u1EA1n v\xE0 c\u1EA7n k\u1EBFt n\u1ED1i l\u1EA1i."
    };
  }
  if (tokenExpiresWithin(token, 24 * 60 * 60 * 1e3)) {
    return {
      status: hasRefreshToken ? "expiring_refreshable" : "expiring",
      label: hasRefreshToken ? "S\u1EAFp h\u1EBFt h\u1EA1n, c\xF3 th\u1EC3 t\u1EF1 l\xE0m m\u1EDBi" : "S\u1EAFp h\u1EBFt h\u1EA1n",
      severity: hasRefreshToken ? "warning" : "error",
      reconnectRequired: !hasRefreshToken,
      hasRefreshToken,
      expiresAt,
      description: hasRefreshToken ? "Token s\u1EBD \u0111\u01B0\u1EE3c t\u1EF1 l\xE0m m\u1EDBi khi c\u1EA7n." : "Token s\u1EAFp h\u1EBFt h\u1EA1n nh\u01B0ng kh\xF4ng c\xF3 refresh token."
    };
  }
  if (reconnectRequired) {
    return {
      status: "reconnect_required",
      label: "C\u1EA7n k\u1EBFt n\u1ED1i l\u1EA1i",
      severity: "error",
      reconnectRequired: true,
      hasRefreshToken,
      expiresAt,
      description: account.last_error || "Phi\xEAn k\u1EBFt n\u1ED1i kh\xF4ng c\xF2n \u1ED5n \u0111\u1ECBnh."
    };
  }
  if (!expiresAt) {
    return {
      status: hasRefreshToken ? "healthy_refreshable" : "healthy",
      label: hasRefreshToken ? "\u1ED4n \u0111\u1ECBnh, c\xF3 refresh token" : "\u1ED4n \u0111\u1ECBnh",
      severity: "success",
      reconnectRequired: false,
      hasRefreshToken,
      expiresAt,
      description: hasRefreshToken ? "K\xEAnh \u0111ang ho\u1EA1t \u0111\u1ED9ng v\xE0 c\xF3 th\u1EC3 t\u1EF1 l\xE0m m\u1EDBi token." : "K\xEAnh \u0111ang ho\u1EA1t \u0111\u1ED9ng \u1ED5n \u0111\u1ECBnh."
    };
  }
  return {
    status: hasRefreshToken ? "healthy_refreshable" : "healthy",
    label: hasRefreshToken ? "\u1ED4n \u0111\u1ECBnh, c\xF3 refresh token" : "\u1ED4n \u0111\u1ECBnh",
    severity: "success",
    reconnectRequired: false,
    hasRefreshToken,
    expiresAt,
    description: "K\xEAnh \u0111ang ho\u1EA1t \u0111\u1ED9ng \u1ED5n \u0111\u1ECBnh."
  };
}
function parseGrantedScopes(scopeValue) {
  if (!scopeValue) return [];
  return Array.from(
    new Set(
      scopeValue.split(/[\s,]+/).map((item) => item.trim()).filter(Boolean)
    )
  );
}
function requiredScopesForPlatform(platform) {
  if (platform === "facebook") return facebookScopes();
  if (platform === "youtube") return youtubeScopes();
  if (platform === "tiktok") return tiktokScopes();
  return [];
}
async function refreshGoogleToken(admin, socialAccountId, tokens) {
  if (!tokens.refresh_token) return tokens;
  const tokenBody = new URLSearchParams({
    client_id: env.googleClientId,
    client_secret: env.googleClientSecret,
    refresh_token: tokens.refresh_token,
    grant_type: "refresh_token"
  });
  const refreshed = await fetchJson("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: tokenBody.toString()
  });
  const nextTokens = {
    ...tokens,
    access_token: refreshed.access_token,
    refresh_token: refreshed.refresh_token || tokens.refresh_token,
    scope: refreshed.scope || tokens.scope,
    token_metadata: refreshed
  };
  await saveTokens(admin, socialAccountId, {
    accessToken: nextTokens.access_token,
    refreshToken: nextTokens.refresh_token,
    expiresIn: refreshed.expires_in,
    scope: nextTokens.scope,
    metadata: nextTokens.token_metadata
  });
  return {
    ...nextTokens,
    token_expires_at: refreshed.expires_in ? new Date(Date.now() + Number(refreshed.expires_in) * 1e3).toISOString() : tokens.token_expires_at
  };
}
async function refreshTikTokToken(admin, socialAccountId, tokens) {
  if (!tokens.refresh_token) return tokens;
  const tokenBody = new URLSearchParams({
    client_key: env.tiktokClientKey,
    client_secret: env.tiktokClientSecret,
    refresh_token: tokens.refresh_token,
    grant_type: "refresh_token"
  });
  const refreshed = await fetchJson("https://open.tiktokapis.com/v2/oauth/token/", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: tokenBody.toString()
  });
  const nextTokens = {
    ...tokens,
    access_token: refreshed.access_token,
    refresh_token: refreshed.refresh_token || tokens.refresh_token,
    scope: refreshed.scope || tokens.scope,
    token_metadata: refreshed
  };
  await saveTokens(admin, socialAccountId, {
    accessToken: nextTokens.access_token,
    refreshToken: nextTokens.refresh_token,
    expiresIn: refreshed.expires_in,
    scope: nextTokens.scope,
    metadata: nextTokens.token_metadata
  });
  return {
    ...nextTokens,
    token_expires_at: refreshed.expires_in ? new Date(Date.now() + Number(refreshed.expires_in) * 1e3).toISOString() : tokens.token_expires_at
  };
}
async function ensureFreshTokens(admin, account, tokens) {
  if (!tokenExpiresSoon(tokens)) return tokens;
  if (account.platform === "youtube") {
    return refreshGoogleToken(admin, account.id, tokens);
  }
  if (account.platform === "tiktok") {
    return refreshTikTokToken(admin, account.id, tokens);
  }
  return tokens;
}
async function markAccountSyncFailure(admin, accountId, errorMessage) {
  await admin.from("social_accounts").update({
    connection_status: "error",
    last_error: errorMessage || "Sync failed",
    last_health_check_at: (/* @__PURE__ */ new Date()).toISOString()
  }).eq("id", accountId);
}
function buildOAuthAuthorizeUrl(platform, state) {
  const redirectUri = `${env.appUrl}/api/oauth/callback/${platform}`;
  if (platform === "facebook") {
    const params2 = new URLSearchParams({
      client_id: env.facebookAppId,
      redirect_uri: redirectUri,
      state,
      response_type: "code",
      scope: facebookScopes().join(",")
    });
    return `https://www.facebook.com/v20.0/dialog/oauth?${params2.toString()}`;
  }
  if (platform === "youtube") {
    const params2 = new URLSearchParams({
      client_id: env.googleClientId,
      redirect_uri: redirectUri,
      state,
      scope: youtubeScopes().join(" "),
      response_type: "code",
      access_type: "offline",
      prompt: "consent"
    });
    return `https://accounts.google.com/o/oauth2/v2/auth?${params2.toString()}`;
  }
  const params = new URLSearchParams({
    client_key: env.tiktokClientKey,
    redirect_uri: redirectUri,
    state,
    scope: tiktokScopes().join(","),
    response_type: "code"
  });
  return `https://www.tiktok.com/v2/auth/authorize/?${params.toString()}`;
}
async function upsertDailyMetrics(admin, workspaceId, socialAccountId, rows) {
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
    raw: row.raw || {}
  }));
  const { error } = await admin.from("daily_channel_metrics").upsert(payload, {
    onConflict: "social_account_id,metric_date"
  });
  if (error) throw error;
}
async function upsertContentSnapshots(admin, workspaceId, socialAccountId, rows) {
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
    snapshot_date: (/* @__PURE__ */ new Date()).toISOString().slice(0, 10),
    reach: row.reach || 0,
    engagement: row.engagement || 0,
    comments: row.comments || 0,
    shares: row.shares || 0,
    saves: row.saves || 0,
    followers_gained: row.followersGained || 0,
    performance_score: row.performanceScore || 0,
    video_views: row.videoViews || 0,
    watch_time_seconds: row.watchTimeSeconds || 0,
    raw: row.raw || {}
  }));
  const { error } = await admin.from("content_snapshots").upsert(payload, {
    onConflict: "social_account_id,platform_content_id"
  });
  if (error) throw error;
}
function computePerformanceScore(reach, engagement) {
  if (!reach) return 0;
  const rate = engagement / Math.max(reach, 1) * 100;
  return Math.max(0, Math.min(100, Math.round(rate * 10)));
}
async function syncYouTubeAccount(admin, account, tokens) {
  const headers = { Authorization: `Bearer ${tokens.access_token}` };
  const channelResp = await fetchJson(
    "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&mine=true",
    { headers }
  );
  const channel = channelResp.items?.[0];
  if (!channel) throw new Error("YouTube channel not found");
  const followers = Number(channel.statistics?.subscriberCount || 0);
  const avatarUrl = channel.snippet?.thumbnails?.medium?.url || channel.snippet?.thumbnails?.default?.url || "";
  const uploadsPlaylistId = channel.contentDetails?.relatedPlaylists?.uploads || "";
  await admin.from("social_accounts").update({
    account_name: channel.snippet?.title || account.account_name,
    account_handle: channel.snippet?.customUrl || account.account_handle,
    avatar_url: avatarUrl,
    follower_count: followers,
    connection_status: "connected",
    last_error: "",
    last_health_check_at: (/* @__PURE__ */ new Date()).toISOString(),
    metadata: {
      ...account.metadata || {},
      view_count: Number(channel.statistics?.viewCount || 0),
      video_count: Number(channel.statistics?.videoCount || 0),
      uploads_playlist_id: uploadsPlaylistId
    }
  }).eq("id", account.id);
  let playlistItems = [];
  if (uploadsPlaylistId) {
    const playlistResp = await fetchJson(
      `https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId=${encodeURIComponent(uploadsPlaylistId)}&maxResults=20`,
      { headers }
    );
    playlistItems = playlistResp.items || [];
  }
  const videoIds = playlistItems.map((item) => item.contentDetails?.videoId).filter(Boolean);
  let videoMap = /* @__PURE__ */ new Map();
  if (videoIds.length) {
    const videosResp = await fetchJson(
      `https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id=${encodeURIComponent(videoIds.join(","))}`,
      { headers }
    );
    videoMap = new Map((videosResp.items || []).map((item) => [item.id, item]));
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
    const thumbnailUrl = video.snippet?.thumbnails?.medium?.url || video.snippet?.thumbnails?.default?.url || "";
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
      raw: video
    };
  });
  await upsertContentSnapshots(admin, account.workspace_id, account.id, contents);
  const endDate = (/* @__PURE__ */ new Date()).toISOString().slice(0, 10);
  const start = /* @__PURE__ */ new Date();
  start.setDate(start.getDate() - 29);
  const startDate = start.toISOString().slice(0, 10);
  let metricRows = [];
  try {
    const analytics = await fetchJson(
      `https://youtubeanalytics.googleapis.com/v2/reports?ids=channel==MINE&startDate=${startDate}&endDate=${endDate}&metrics=views,comments,likes,shares,subscribersGained,subscribersLost,estimatedMinutesWatched,averageViewDuration&dimensions=day&sort=day`,
      { headers }
    );
    metricRows = (analytics.rows || []).map((row) => ({
      metricDate: row[0],
      followers,
      followersGained: Number(row[5] || 0) - Number(row[6] || 0),
      reach: Number(row[1] || 0),
      impressions: Number(row[1] || 0),
      engagement: Number(row[2] || 0) + Number(row[3] || 0) + Number(row[4] || 0),
      videoViews: Number(row[1] || 0),
      watchTimeSeconds: Math.round(Number(row[7] || 0) * 60),
      comments: Number(row[2] || 0),
      shares: Number(row[4] || 0),
      saves: 0,
      raw: { averageViewDuration: Number(row[8] || 0) }
    }));
  } catch {
    metricRows = [];
  }
  if (!metricRows.length) {
    const grouped = /* @__PURE__ */ new Map();
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
        raw: {}
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
async function syncTikTokAccount(admin, account, tokens) {
  const headers = { Authorization: `Bearer ${tokens.access_token}` };
  const userInfo = await fetchJson(
    "https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,avatar_url,display_name,follower_count,likes_count,video_count",
    { headers }
  );
  const user = userInfo.data?.user || {};
  const followers = Number(user.follower_count || 0);
  await admin.from("social_accounts").update({
    account_name: user.display_name || account.account_name,
    avatar_url: user.avatar_url || account.avatar_url,
    follower_count: followers,
    connection_status: "connected",
    last_error: "",
    last_health_check_at: (/* @__PURE__ */ new Date()).toISOString(),
    metadata: {
      ...account.metadata || {},
      union_id: user.union_id || "",
      likes_count: Number(user.likes_count || 0),
      video_count: Number(user.video_count || 0)
    }
  }).eq("id", account.id);
  const listed = await fetchJson("https://open.tiktokapis.com/v2/video/list/", {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ max_count: 20 })
  });
  const listedVideos = listed.data?.videos || [];
  const videoIds = listedVideos.map((item) => item.id).filter(Boolean);
  let videos = [];
  if (videoIds.length) {
    const queried = await fetchJson(
      "https://open.tiktokapis.com/v2/video/query/?fields=id,create_time,title,cover_image_url,share_url,video_description,duration,like_count,comment_count,share_count,view_count",
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ filters: { video_ids: videoIds } })
      }
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
      publishedAt: video.create_time ? new Date(Number(video.create_time) * 1e3).toISOString() : null,
      reach: views,
      engagement,
      comments,
      shares,
      saves: 0,
      followersGained: 0,
      performanceScore: computePerformanceScore(views, engagement),
      videoViews: views,
      watchTimeSeconds: Number(video.duration || 0),
      raw: video
    };
  });
  await upsertContentSnapshots(admin, account.workspace_id, account.id, contents);
  const grouped = /* @__PURE__ */ new Map();
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
      raw: {}
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
async function syncFacebookAccount(admin, account, tokens) {
  const base = "https://graph.facebook.com/v20.0";
  const page = await fetchJson(
    `${base}/${encodeURIComponent(account.account_platform_id)}?fields=id,name,fan_count,followers_count,picture{url}&access_token=${encodeURIComponent(tokens.access_token)}`
  );
  const followers = Number(page.followers_count || page.fan_count || 0);
  await admin.from("social_accounts").update({
    account_name: page.name || account.account_name,
    avatar_url: page.picture?.data?.url || account.avatar_url,
    follower_count: followers,
    connection_status: "connected",
    last_error: "",
    last_health_check_at: (/* @__PURE__ */ new Date()).toISOString()
  }).eq("id", account.id);
  const posts = await fetchJson(
    `${base}/${encodeURIComponent(account.account_platform_id)}/posts?fields=id,message,created_time,full_picture,permalink_url,shares,reactions.summary(true),comments.summary(true)&limit=20&access_token=${encodeURIComponent(tokens.access_token)}`
  );
  const rows = posts.data || [];
  const contents = rows.map((post2) => {
    const comments = Number(post2.comments?.summary?.total_count || 0);
    const shares = Number(post2.shares?.count || 0);
    const reactions = Number(post2.reactions?.summary?.total_count || 0);
    const reach = reactions * 12 + comments * 8 + shares * 20;
    const engagement = reactions + comments + shares;
    return {
      platformContentId: String(post2.id),
      title: (post2.message || "Facebook post").slice(0, 80),
      caption: post2.message || "",
      contentType: "post",
      thumbnailUrl: post2.full_picture || "",
      permalink: post2.permalink_url || "",
      publishedAt: post2.created_time || null,
      reach,
      engagement,
      comments,
      shares,
      saves: 0,
      followersGained: 0,
      performanceScore: computePerformanceScore(reach, engagement),
      videoViews: 0,
      watchTimeSeconds: 0,
      raw: post2
    };
  });
  await upsertContentSnapshots(admin, account.workspace_id, account.id, contents);
  let metrics = [];
  try {
    const insights = await fetchJson(
      `${base}/${encodeURIComponent(account.account_platform_id)}/insights?metric=page_impressions,page_post_engagements,page_fans&period=day&access_token=${encodeURIComponent(tokens.access_token)}`
    );
    const metricMap = {};
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
          raw: {}
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
    const grouped = /* @__PURE__ */ new Map();
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
        raw: {}
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
async function syncAccount(admin, account) {
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
async function buildStateV2(admin, user, workspaceContext) {
  const workspaceId = workspaceContext.workspace.id;
  const [{ data: groups }, { data: accounts }, { data: dailyMetrics }, { data: contents }, { data: inbox }, { data: settings }, { data: members }, { data: profile }] = await Promise.all([
    admin.from("channel_groups").select("*").eq("workspace_id", workspaceId).eq("is_archived", false).order("position"),
    admin.from("social_accounts").select("*").eq("workspace_id", workspaceId).order("platform").order("account_name"),
    admin.from("daily_channel_metrics").select("*").eq("workspace_id", workspaceId).gte("metric_date", new Date(Date.now() - 29 * 864e5).toISOString().slice(0, 10)).order("metric_date"),
    admin.from("content_snapshots").select("*").eq("workspace_id", workspaceId).order("published_at", { ascending: false }).limit(200),
    admin.from("inbox_messages").select("*").eq("workspace_id", workspaceId).order("received_at", { ascending: false }).limit(50),
    admin.from("user_settings").select("*").eq("user_id", user.id).maybeSingle(),
    admin.from("workspace_members").select("id, user_id, role, profile:profiles(full_name, email, avatar_url, username)").eq("workspace_id", workspaceId),
    admin.from("profiles").select("*").eq("id", user.id).maybeSingle()
  ]);
  const accountRows = accounts || [];
  const accountIds = accountRows.map((item) => item.id);
  const { data: tokenRows } = accountIds.length ? await admin.from("social_account_tokens").select("*").in("social_account_id", accountIds) : { data: [] };
  const metricRows = dailyMetrics || [];
  const contentRows = contents || [];
  const inboxRows = inbox || [];
  const groupRows = groups || [];
  const memberRows = members || [];
  const tokensByAccount = new Map((tokenRows || []).map((item) => [item.social_account_id, item]));
  const groupMap = new Map(groupRows.map((item) => [item.id, item]));
  const memberByUserId = new Map(memberRows.map((item) => [item.user_id, item]));
  const metricsByAccount = /* @__PURE__ */ new Map();
  for (const metric of metricRows) {
    const key = metric.social_account_id;
    if (!metricsByAccount.has(key)) metricsByAccount.set(key, []);
    metricsByAccount.get(key).push(metric);
  }
  const workspaceFollowers = accountRows.reduce((sum, item) => sum + Number(item.follower_count || 0), 0);
  const serializedGroups = [
    {
      id: "all",
      name: "T\u1EA5t c\u1EA3 k\xEAnh (Workspace)",
      channelsCount: accountRows.length,
      followers: compactNumber(workspaceFollowers),
      health: accountRows.some((item) => item.connection_status === "error") ? "error" : accountRows.some((item) => item.connection_status === "warning") ? "warning" : "healthy",
      platforms: Array.from(new Set(accountRows.map((item) => item.platform))),
      isPinned: true
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
        description: group.description || ""
      };
    })
  ];
  const serializedChannels = accountRows.map((item) => {
    const token = tokensByAccount.get(item.id);
    const metadata = item.metadata || {};
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
      lastSync: item.last_health_check_at ? new Date(item.last_health_check_at).toLocaleString("vi-VN") : "Ch\u01B0a \u0111\u1ED3ng b\u1ED9",
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
      groupName: groupMap.get(item.channel_group_id || "")?.name || "Ch\u01B0a ph\xE2n nh\xF3m",
      rawMetadata: metadata
    };
  });
  const serializedContents = contentRows.map((item, index) => {
    const account = accountRows.find((row) => row.id === item.social_account_id);
    return {
      id: item.id,
      thumbnail: item.thumbnail_url || `https://picsum.photos/seed/${item.id}/200/200`,
      title: item.title || "N\u1ED9i dung ch\u01B0a \u0111\u1EB7t t\xEAn",
      caption: item.caption || "",
      channel: account?.account_name || "K\xEAnh",
      channelId: item.social_account_id,
      groupId: account?.channel_group_id || "all",
      platform: account?.platform || "facebook",
      date: item.published_at || (/* @__PURE__ */ new Date()).toISOString(),
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
      pillar: ["Gi\xE1o d\u1EE5c", "S\u1EA3n ph\u1EA9m", "H\u1EADu tr\u01B0\u1EDDng", "Kh\xE1ch h\xE0ng", "Xu h\u01B0\u1EDBng"][index % 5],
      growthImpact: Number(item.performance_score || 0) >= 85 ? "+High" : "Medium",
      engagementRate: Number(item.reach || 0) > 0 ? Math.round(Number(item.engagement || 0) / Math.max(Number(item.reach || 0), 1) * 1e3) / 10 : 0,
      videoViews: Number(item.video_views || 0),
      watchTimeSeconds: Number(item.watch_time_seconds || 0)
    };
  });
  const serializedPosts = contentRows.map((item) => {
    const account = accountRows.find((row) => row.id === item.social_account_id);
    const effectiveDate = item.published_at ? new Date(item.published_at) : /* @__PURE__ */ new Date();
    const today = /* @__PURE__ */ new Date();
    return {
      id: item.id,
      postId: item.id,
      title: item.title || "N\u1ED9i dung",
      time: effectiveDate.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }),
      date: effectiveDate.toISOString().slice(0, 10),
      dateOffset: Math.round((effectiveDate.getTime() - today.getTime()) / 864e5),
      platform: account?.platform || "facebook",
      channel: account?.account_name || "K\xEAnh",
      status: "published",
      type: item.content_type || "post",
      perfScore: Number(item.performance_score || 0),
      content: item.caption || "",
      caption: item.caption || "",
      accountId: item.social_account_id
    };
  });
  const trendMap = /* @__PURE__ */ new Map();
  for (const metric of metricRows) {
    const date = metric.metric_date;
    if (!trendMap.has(date)) {
      trendMap.set(date, {
        date: (/* @__PURE__ */ new Date(`${date}T00:00:00Z`)).toLocaleDateString("en-US", { month: "short", day: "2-digit", timeZone: "UTC" }),
        facebook: 0,
        youtube: 0,
        tiktok: 0,
        total: 0
      });
    }
    const row = trendMap.get(date);
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
    { reach: 0, engagement: 0, followers: 0, views: 0 }
  );
  const kpis = [
    { title: "T\u1ED5ng Reach", value: compactNumber(totals.reach), change: "+0%", trend: "up", period: "30 ng\xE0y", platforms: ["facebook", "youtube", "tiktok"], trendData: [2, 4, 5, 7, 8, 10] },
    { title: "T\u1ED5ng T\u01B0\u01A1ng T\xE1c", value: compactNumber(totals.engagement), change: "+0%", trend: "up", period: "30 ng\xE0y", platforms: ["facebook", "youtube", "tiktok"], trendData: [3, 3, 5, 6, 8, 9] },
    { title: "Followers M\u1EDBi", value: compactNumber(totals.followers), change: "+0%", trend: "up", period: "30 ng\xE0y", platforms: ["facebook", "youtube", "tiktok"], trendData: [1, 2, 2, 4, 5, 6] },
    { title: "L\u01B0\u1EE3t Xem Video", value: compactNumber(totals.views), change: "+0%", trend: "up", period: "30 ng\xE0y", platforms: ["youtube", "tiktok"], trendData: [2, 5, 4, 8, 9, 11] },
    { title: "N\u1ED9i Dung", value: compactNumber(contentRows.length), change: "read only", trend: "up", period: "to\xE0n b\u1ED9", platforms: ["facebook", "youtube", "tiktok"], trendData: [1, 2, 3, 3, 4, 5] },
    { title: "T\u1EA7n Su\u1EA5t \u0110\u1ED3ng B\u1ED9", value: accountRows.length ? "100%" : "0%", change: "health check", trend: "up", period: "h\u1EC7 th\u1ED1ng", platforms: ["facebook", "youtube", "tiktok"], trendData: [4, 4, 5, 5, 6, 6] }
  ];
  const alerts = serializedChannels.filter(
    (item) => item.connectionStatus !== "connected" || item.missingScopes.length > 0 || ["expiring", "expiring_refreshable", "expired", "expired_refreshable", "reconnect_required", "missing"].includes(item.tokenHealth.status)
  ).map((item) => ({
    id: `status-${item.id}`,
    title: item.missingScopes.length > 0 ? `Scope ${item.platform} c\u1EE7a ${item.name} \u0111ang thi\u1EBFu` : item.connectionStatus !== "connected" ? `K\u1EBFt n\u1ED1i ${item.platform} c\u1EA7n ki\u1EC3m tra` : `Token ${item.platform} c\u1EE7a ${item.name} c\u1EA7n ch\xFA \xFD`,
    message: item.missingScopes.length > 0 ? `Thi\u1EBFu ${item.missingScopes.length} quy\u1EC1n: ${item.missingScopes.join(", ")}` : item.lastError || item.tokenHealth.description || "Token ho\u1EB7c phi\xEAn k\u1EBFt n\u1ED1i kh\xF4ng c\xF2n \u1ED5n \u0111\u1ECBnh.",
    type: item.tokenHealth.severity === "error" ? "warning" : "info",
    severity: item.tokenHealth.severity === "error" ? "warning" : item.tokenHealth.severity,
    time: "hi\u1EC7n t\u1EA1i"
  }));
  const selectedAccount = accountRows[0] || null;
  const selectedMetrics = selectedAccount ? metricsByAccount.get(selectedAccount.id) || [] : [];
  const selectedInbox = selectedAccount ? inboxRows.filter((item) => item.social_account_id === selectedAccount.id) : [];
  const heatMapDays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const heatCounter = /* @__PURE__ */ new Map();
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
      value: heatCounter.get(`${day}:${hour}`) || 0
    }))
  }));
  const selectedSerializedChannel = selectedAccount ? serializedChannels.find((item) => item.id === selectedAccount.id) || null : null;
  const channelAnalytics = selectedAccount ? {
    selected: selectedSerializedChannel,
    summary: {
      groupName: groupMap.get(selectedAccount.channel_group_id || "")?.name || "Ch\u01B0a ph\xE2n nh\xF3m",
      connectionLabel: selectedSerializedChannel?.reconnectRequired ? "C\u1EA7n k\u1EBFt n\u1ED1i l\u1EA1i" : "K\u1EBFt n\u1ED1i \u1ED5n \u0111\u1ECBnh",
      syncLabel: selectedAccount.last_health_check_at ? "V\u1EEBa xong" : "Ch\u01B0a \u0111\u1ED3ng b\u1ED9",
      handle: selectedAccount.account_handle || selectedAccount.account_platform_id,
      avgResponseMinutes: 0,
      latestReach: Number(selectedMetrics[selectedMetrics.length - 1]?.reach || 0),
      previousReach: Number(selectedMetrics[selectedMetrics.length - 2]?.reach || 0),
      latestEngagement: Number(selectedMetrics[selectedMetrics.length - 1]?.engagement || 0),
      videoViews: selectedMetrics.reduce((sum, row) => sum + Number(row.video_views || 0), 0)
    },
    kpis: [
      { label: "Followers", value: compactNumber(selectedAccount.follower_count), change: "+0%", trend: "up" },
      { label: "Video Views", value: compactNumber(selectedMetrics.reduce((sum, row) => sum + Number(row.video_views || 0), 0)), change: "+0%", trend: "up" },
      { label: "Watch Time", value: compactNumber(Math.round(selectedMetrics.reduce((sum, row) => sum + Number(row.watch_time_seconds || 0), 0) / 3600)), change: "+0%", trend: "up" },
      { label: "Avg Response", value: "0m", change: "read only", trend: "up" },
      { label: "Engagement", value: compactNumber(selectedMetrics.reduce((sum, row) => sum + Number(row.engagement || 0), 0)), change: "+0%", trend: "up" },
      { label: "Reach", value: compactNumber(selectedMetrics.reduce((sum, row) => sum + Number(row.reach || 0), 0)), change: "+0%", trend: "up" }
    ],
    trendData: selectedMetrics.map((row) => ({
      date: (/* @__PURE__ */ new Date(`${row.metric_date}T00:00:00Z`)).toLocaleDateString("en-US", { month: "short", day: "2-digit", timeZone: "UTC" }),
      total: Number(row.reach || 0),
      [selectedAccount.platform]: Number(row.reach || 0)
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
      replies: []
    })),
    channels: serializedChannels,
    topContent: serializedContents.filter((item) => item.channelId === selectedAccount.id).slice(0, 8)
  } : { channels: [], trendData: [], heatmapData: [], selected: null };
  const platformData = Object.entries(
    serializedChannels.reduce((acc, item) => {
      const parsed = Number(String(item.followers).replace(/[^\d.]/g, "")) || 0;
      acc[item.platform] = (acc[item.platform] || 0) + parsed;
      return acc;
    }, {})
  ).map(([name, value]) => ({ name: name.charAt(0).toUpperCase() + name.slice(1), value }));
  return {
    workspace: workspaceContext.workspace,
    user: {
      name: profile?.full_name || user.user_metadata?.full_name || user.email,
      email: user.email,
      username: profile?.username || user.user_metadata?.username || user.email?.split("@")[0] || "",
      role: workspaceContext.membership.role.toUpperCase(),
      avatar: profile?.avatar_url || ""
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
        alerts: settings?.alert_notifications ?? true
      }
    },
    systemUsers: memberRows.map((item) => ({
      id: item.id,
      name: item.profile?.full_name || item.profile?.email || "User",
      email: item.profile?.email || "",
      role: String(item.role || "viewer").toUpperCase(),
      status: "Dang hoat dong",
      avatar: item.profile?.avatar_url || `https://api.dicebear.com/7.x/identicon/svg?seed=${item.id}`
    })),
    reports: {
      kpis: [
        { title: "Tong Reach", value: compactNumber(totals.reach), delta: 0, sparklineData: trendData.map((item) => item.total) },
        { title: "Ti le Tuong Tac", value: `${Math.round(totals.engagement / Math.max(totals.reach, 1) * 1e3) / 10}%`, delta: 0, sparklineData: trendData.map((item) => item.total) },
        { title: "Follower Moi", value: compactNumber(totals.followers), delta: 0, sparklineData: trendData.map((item) => item.total) },
        { title: "Video Views", value: compactNumber(totals.views), delta: 0, sparklineData: trendData.map((item) => item.total) }
      ],
      viewsData: trendData.map((item) => ({ name: item.date, views: item.total, engagement: item.total })),
      platformData,
      compact: [
        { title: "Tin Nhan Moi", value: compactNumber(inboxRows.length), delta: 0 },
        { title: "Binh Luan", value: compactNumber(serializedContents.reduce((sum, item) => sum + Number(item.comments || 0), 0)), delta: 0 },
        { title: "Chia Se", value: compactNumber(serializedContents.reduce((sum, item) => sum + Number(item.shares || 0), 0)), delta: 0 },
        { title: "Luu Bai", value: compactNumber(serializedContents.reduce((sum, item) => sum + Number(item.saves || 0), 0)), delta: 0 }
      ]
    },
    channelAnalytics,
    urls: {
      connectChannel: `${env.appUrl}/api/oauth/start`,
      logout: `${env.appUrl}/login`
    }
  };
}
function facebookScopes() {
  return [
    "pages_show_list",
    "pages_read_engagement",
    "pages_read_user_content",
    "read_insights",
    "pages_manage_engagement"
  ];
}
function youtubeScopes() {
  return [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl"
  ];
}
function tiktokScopes() {
  return ["user.info.basic", "user.info.profile", "user.info.stats", "video.list"];
}
async function handleOAuthStart(event, admin, user) {
  const platform = queryValue(event, "platform");
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
    ts: String(Date.now())
  });
  return oauthRedirect(buildOAuthAuthorizeUrl(platform, state));
}
async function handleOAuthCallback(event, admin) {
  const platform = getPath(event).split("/").filter(Boolean)[2];
  const code = queryValue(event, "code");
  const stateValue = queryValue(event, "state");
  const error = queryValue(event, "error");
  if (error) {
    return redirect(`${env.appUrl}/manage?oauth_error=${encodeURIComponent(error)}`);
  }
  if (!code || !stateValue) {
    return redirect(`${env.appUrl}/manage?oauth_error=missing_code`);
  }
  let state;
  try {
    state = verifyState(stateValue);
  } catch (stateError) {
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
      grant_type: "authorization_code"
    });
    const token2 = await fetchJson("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: tokenBody.toString()
    });
    const profile = await fetchJson(
      "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&mine=true",
      { headers: { Authorization: `Bearer ${token2.access_token}` } }
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
        auth_account_id: channel.id
      }
    });
    await saveTokens(admin, account.id, {
      accessToken: token2.access_token,
      refreshToken: token2.refresh_token,
      expiresIn: token2.expires_in,
      scope: token2.scope,
      metadata: token2
    });
    await syncYouTubeAccount(admin, account, { access_token: token2.access_token });
    return redirect(`${env.appUrl}/manage?connected=youtube`);
  }
  if (platform === "tiktok") {
    const tokenBody = new URLSearchParams({
      client_key: env.tiktokClientKey,
      client_secret: env.tiktokClientSecret,
      code,
      grant_type: "authorization_code",
      redirect_uri: redirectUri
    });
    const token2 = await fetchJson("https://open.tiktokapis.com/v2/oauth/token/", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: tokenBody.toString()
    });
    const userInfo = await fetchJson(
      "https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,avatar_url,display_name,follower_count",
      { headers: { Authorization: `Bearer ${token2.access_token}` } }
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
        auth_account_id: user.open_id || ""
      }
    });
    await saveTokens(admin, account.id, {
      accessToken: token2.access_token,
      refreshToken: token2.refresh_token,
      expiresIn: token2.expires_in,
      scope: token2.scope,
      metadata: token2
    });
    await syncTikTokAccount(admin, account, { access_token: token2.access_token });
    return redirect(`${env.appUrl}/manage?connected=tiktok`);
  }
  const shortToken = await fetchJson(
    `https://graph.facebook.com/v20.0/oauth/access_token?client_id=${encodeURIComponent(env.facebookAppId)}&client_secret=${encodeURIComponent(env.facebookAppSecret)}&redirect_uri=${encodeURIComponent(redirectUri)}&code=${encodeURIComponent(code)}`
  );
  const token = await fetchJson(
    `https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id=${encodeURIComponent(env.facebookAppId)}&client_secret=${encodeURIComponent(env.facebookAppSecret)}&fb_exchange_token=${encodeURIComponent(shortToken.access_token)}`
  ).catch(() => shortToken);
  const authProfile = await fetchJson(
    `https://graph.facebook.com/v20.0/me?fields=id,name&access_token=${encodeURIComponent(token.access_token)}`
  ).catch(() => ({ id: "", name: "" }));
  const pages = await fetchJson(
    `https://graph.facebook.com/v20.0/me/accounts?fields=id,name,access_token,picture{url},followers_count,fan_count&access_token=${encodeURIComponent(token.access_token)}`
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
        auth_account_id: authProfile.id || ""
      }
    });
    await saveTokens(admin, account.id, {
      accessToken: page.access_token,
      metadata: { source_token: token.access_token }
    });
    await syncFacebookAccount(admin, account, { access_token: page.access_token });
  }
  return redirect(`${env.appUrl}/manage?connected=facebook`);
}
async function handleTokenImport(event, admin, user) {
  const workspace = await ensureWorkspaceForUser(admin, user);
  const body = parseBody(event);
  const platform = String(body.platform || "");
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
    const page = await fetchJson(
      `https://graph.facebook.com/v20.0/${encodeURIComponent(externalId)}?fields=id,name,fan_count,followers_count,picture{url}&access_token=${encodeURIComponent(accessToken)}`
    );
    const account2 = await upsertAccount(admin, {
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
        auth_account_id: String(page.id || externalId)
      }
    });
    await saveTokens(admin, account2.id, {
      accessToken,
      scope,
      metadata: { import_mode: "manual_token" }
    });
    await syncFacebookAccount(admin, account2, { access_token: accessToken });
    return response(200, { ok: true, platform: "facebook", accountId: account2.id });
  }
  if (platform === "youtube") {
    const channelResp = await fetchJson(
      "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&mine=true",
      { headers: { Authorization: `Bearer ${accessToken}` } }
    );
    const channel = channelResp.items?.[0];
    if (!channel) {
      return response(400, { error: "YouTube token is valid but no channel was found for the current account" });
    }
    const account2 = await upsertAccount(admin, {
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
        auth_account_id: String(channel.id)
      }
    });
    await saveTokens(admin, account2.id, {
      accessToken,
      refreshToken: refreshToken || void 0,
      expiresIn: Number.isFinite(expiresIn) && expiresIn > 0 ? expiresIn : void 0,
      scope,
      metadata: { import_mode: "manual_token" }
    });
    await syncYouTubeAccount(admin, account2, { access_token: accessToken, refresh_token: refreshToken || void 0 });
    return response(200, { ok: true, platform: "youtube", accountId: account2.id });
  }
  const userInfo = await fetchJson(
    "https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,avatar_url,display_name,follower_count,likes_count,video_count",
    { headers: { Authorization: `Bearer ${accessToken}` } }
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
      auth_account_id: String(tiktokUser.open_id)
    }
  });
  await saveTokens(admin, account.id, {
    accessToken,
    refreshToken: refreshToken || void 0,
    expiresIn: Number.isFinite(expiresIn) && expiresIn > 0 ? expiresIn : void 0,
    scope,
    metadata: { import_mode: "manual_token" }
  });
  await syncTikTokAccount(admin, account, { access_token: accessToken, refresh_token: refreshToken || void 0 });
  return response(200, { ok: true, platform: "tiktok", accountId: account.id });
}
async function handleChannelAction(event, admin, user, accountId) {
  const body = parseBody(event);
  const action = body.action;
  const { data: account, error } = await admin.from("social_accounts").select("*").eq("id", accountId).single();
  if (error || !account) return response(404, { error: "Channel not found" });
  const membership = await getWorkspaceMembership(admin, account.workspace_id, user.id);
  if (!membership) return response(403, { error: "Forbidden" });
  if (action === "sync") {
    try {
      await syncAccount(admin, account);
      return response(200, { ok: true });
    } catch (syncError) {
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
      ts: String(Date.now())
    });
    return response(200, { redirect: buildOAuthAuthorizeUrl(account.platform, state) });
  }
  return response(400, { error: "Unsupported action" });
}
async function handleChannelPatch(event, admin, user, accountId) {
  const body = parseBody(event);
  const { data: account, error } = await admin.from("social_accounts").select("*").eq("id", accountId).single();
  if (error || !account) return response(404, { error: "Channel not found" });
  const membership = await getWorkspaceMembership(admin, account.workspace_id, user.id);
  if (!membership) return response(403, { error: "Forbidden" });
  const updates = {};
  if (body.groupId !== void 0) {
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
async function handleChannelDelete(event, admin, user, accountId) {
  const { data: account, error } = await admin.from("social_accounts").select("*").eq("id", accountId).single();
  if (error || !account) return response(404, { error: "Channel not found" });
  const membership = await getWorkspaceMembership(admin, account.workspace_id, user.id);
  if (!membership) return response(403, { error: "Forbidden" });
  const { error: deleteError } = await admin.from("social_accounts").delete().eq("id", accountId);
  if (deleteError) return response(400, { error: deleteError.message });
  return response(200, { ok: true });
}
async function handleGroups(event, admin, user, groupId) {
  const workspace = await ensureWorkspaceForUser(admin, user);
  const body = parseBody(event);
  if (event.httpMethod === "POST") {
    if (!body.name) return response(400, { error: "Group name is required" });
    const { data, error: error2 } = await admin.from("channel_groups").insert({
      workspace_id: workspace.workspace.id,
      name: String(body.name).trim(),
      description: String(body.description || ""),
      position: Math.max(1, Date.now() % 1e4)
    }).select("*").single();
    if (error2) return response(400, { error: error2.message });
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
  const { error: patchError } = await admin.from("channel_groups").update({
    name: body.name ? String(body.name).trim() : group.name,
    description: body.description !== void 0 ? String(body.description) : group.description
  }).eq("id", groupId);
  if (patchError) return response(400, { error: patchError.message });
  return response(200, { ok: true });
}
async function handleSettings(event, admin, user) {
  const body = parseBody(event);
  const notifications = body.notifications || {};
  const profile = body.profile || {};
  await admin.from("user_settings").upsert({
    user_id: user.id,
    email_notifications: notifications.email ?? true,
    push_notifications: notifications.push ?? true,
    alert_notifications: notifications.alerts ?? true
  });
  if (profile.name) {
    await admin.from("profiles").upsert({
      id: user.id,
      email: user.email,
      full_name: String(profile.name)
    });
  }
  return response(200, { ok: true });
}
var TOKEN_HEALTH_PREFIX = "[TOKEN_HEALTH]";
async function applyTokenHealthStatus(admin, account, token) {
  const tokenHealth = describeTokenHealth(account, token);
  const warningStatuses = /* @__PURE__ */ new Set(["expiring", "expiring_refreshable", "expired_refreshable"]);
  const reconnectStatuses = /* @__PURE__ */ new Set(["expired", "reconnect_required", "missing"]);
  const currentError = String(account.last_error || "");
  const nextMessage = `${TOKEN_HEALTH_PREFIX} ${tokenHealth.description}`;
  if (reconnectStatuses.has(tokenHealth.status)) {
    await admin.from("social_accounts").update({
      connection_status: "error",
      last_error: nextMessage,
      last_health_check_at: (/* @__PURE__ */ new Date()).toISOString()
    }).eq("id", account.id);
    return { id: account.id, status: tokenHealth.status, severity: "error", changed: true };
  }
  if (warningStatuses.has(tokenHealth.status)) {
    await admin.from("social_accounts").update({
      connection_status: account.connection_status === "error" ? account.connection_status : "warning",
      last_error: currentError && !currentError.startsWith(TOKEN_HEALTH_PREFIX) ? currentError : nextMessage,
      last_health_check_at: (/* @__PURE__ */ new Date()).toISOString()
    }).eq("id", account.id);
    return { id: account.id, status: tokenHealth.status, severity: "warning", changed: true };
  }
  if (currentError.startsWith(TOKEN_HEALTH_PREFIX) || account.connection_status === "warning") {
    await admin.from("social_accounts").update({
      connection_status: "connected",
      last_error: currentError.startsWith(TOKEN_HEALTH_PREFIX) ? "" : currentError,
      last_health_check_at: (/* @__PURE__ */ new Date()).toISOString()
    }).eq("id", account.id);
    return { id: account.id, status: tokenHealth.status, severity: "success", changed: true };
  }
  return { id: account.id, status: tokenHealth.status, severity: "success", changed: false };
}
async function handleCronTokenHealth(event, admin) {
  const providedSecret = event.headers["x-cron-secret"] || event.headers["X-Cron-Secret"];
  if (!env.cronSecret || providedSecret !== env.cronSecret) {
    return response(401, { error: "Unauthorized" });
  }
  const { data: accounts, error } = await admin.from("social_accounts").select("*");
  if (error) return response(500, { error: error.message });
  const results = [];
  for (const account of accounts || []) {
    try {
      const token = await getTokens(admin, account.id);
      const result = await applyTokenHealthStatus(admin, account, token);
      results.push(result);
    } catch (scanError) {
      await admin.from("social_accounts").update({
        connection_status: "error",
        last_error: `${TOKEN_HEALTH_PREFIX} ${scanError.message || "Kh\xF4ng th\u1EC3 ki\u1EC3m tra token"}`,
        last_health_check_at: (/* @__PURE__ */ new Date()).toISOString()
      }).eq("id", account.id);
      results.push({
        id: account.id,
        status: "scan_failed",
        severity: "error",
        changed: true,
        error: scanError.message || "Token health scan failed"
      });
    }
  }
  return response(200, { scanned: results.length, results });
}
async function handleCronSync(event, admin) {
  const providedSecret = event.headers["x-cron-secret"] || event.headers["X-Cron-Secret"];
  if (!env.cronSecret || providedSecret !== env.cronSecret) {
    return response(401, { error: "Unauthorized" });
  }
  const { data: accounts, error } = await admin.from("social_accounts").select("*");
  if (error) return response(500, { error: error.message });
  const results = [];
  for (const account of accounts || []) {
    try {
      await syncAccount(admin, account);
      results.push({ id: account.id, ok: true });
    } catch (syncError) {
      await markAccountSyncFailure(admin, account.id, syncError.message || "Sync failed");
      results.push({ id: account.id, ok: false, error: syncError.message || "Sync failed" });
    }
  }
  return response(200, { synced: results.length, results });
}
async function handler(event) {
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
    if (path === "/posts" || path.startsWith("/posts/") || path === "/media" || path === "/inbox" || path.startsWith("/inbox/") || path === "/members" || path.startsWith("/members/")) {
      return response(501, {
        error: "Tinh nang nay dang phat trien cho phien ban read-only analytics."
      });
    }
    return response(404, { error: "Not found" });
  } catch (error) {
    return response(500, { error: error.message || "Unexpected server error" });
  }
}
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  handler
});
//# sourceMappingURL=api.js.map
