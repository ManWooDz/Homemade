import { useLocale } from "./context/LocaleContext";
import { useState, useEffect, useRef, useLayoutEffect, useMemo, useCallback } from "react";
import {
    Home,
    Refrigerator,
    CookingPot,
    Heart,
    User,
    Search,
    SlidersHorizontal,
    Plus,
    X,
} from "lucide-react";
import logo from "./assets/HomeMade_Logo.png";
import BottomMenu from "./components/bottomMenu";
import RecipeDetail from "./pages/RecipeDetail";
import CreateRecipe from "./pages/CreateRecipe";
import CookingPage from "./pages/CookingPage";
import UserIngredients from "./pages/UserIngredients";
import CustomCookingPage from "./pages/CustomCookingPage";
import AddIngredient from "./pages/AddIngredient";
import BarcodeScanPage from "./pages/BarcodeScanPage";
import IngredientDetail from "./pages/IngredientDetail";
import Favorites from "./pages/Favorites";
import DragScrollRow from "./components/DragScrollRow";
import Profile from "./pages/Profile";
import HistoryDetail from "./pages/HistoryDetail";
import NotificationBell from "./components/NotificationBell";
import NotificationToast from "./components/NotificationToast";
import Notifications from "./pages/Notifications";
import { bangkokDate } from "./utils/expiry";
import { toPresenceIngredients } from "./utils/ingredientPayload";
import { toUserFacingGenerateError, validateAllergyPreferences } from "./utils/generateError";
import { getTagColor } from "./utils/tagColors";
import { useAuth } from "./context/AuthContext";

const toHistoryItem = (row) => ({
    ...row.recipe_data,
    id: row.id,
    image: row.image,
    created_at: row.created_at,
    is_favorite: row.is_favorite,
    stars: row.rating?.stars ?? 0,
    tag: row.rating?.tag ?? null,
    feedback: row.rating?.feedback ?? null,
});

function App() {
    const { t, locale } = useLocale();
    const { apiFetch, user } = useAuth();

    const [activeTab, setActiveTab] = useState("home");
    const [currentView, setCurrentView] = useState("home"); // "home" | "recipe-detail" | "create-recipe" | "cooking-page" | "user-ingredients" | "custom-cooking"
    const [selectedIngredients, setSelectedIngredients] = useState([]);
    const [userIngredients, setUserIngredients] = useState([]);
    const [selectedRecipe, setSelectedRecipe] = useState(null);
    const [favoriteRecipeIds, setFavoriteRecipeIds] = useState([]);
    const [selectedHistoryItem, setSelectedHistoryItem] = useState(null);
    const [historyReturnView, setHistoryReturnView] = useState("profile");
    const [favoritesTab, setFavoritesTab] = useState("base"); // "base" | "mine"
    const [cookingHistory, setCookingHistory] = useState([]);
    const [profileView, setProfileView] = useState("main");
    const [historyBrowse, setHistoryBrowse] = useState({ query: "", favorite: "all", rating: "all" });
    const historySessionRef = useRef(null);
    useLayoutEffect(() => {
        historySessionRef.current = { pending: new Set() };
        return () => { historySessionRef.current = null; };
    }, []);
    const [barcodePrefill, setBarcodePrefill] = useState(null);
    const [selectedIngredientDetail, setSelectedIngredientDetail] = useState(null);

    const [recipes, setRecipes] = useState([]);
    const [categories, setCategories] = useState(["All"]);
    const [selectedCategory, setSelectedCategory] = useState("All");

    const [searchQuery, setSearchQuery] = useState("");
    const [showFilterPanel, setShowFilterPanel] = useState(false);
    const [filterTab, setFilterTab] = useState("ingredient");
    const [filterIngredientQuery, setFilterIngredientQuery] = useState("");
    const [selectedIngredientNames, setSelectedIngredientNames] = useState([]);
    const [selectedMealTypes, setSelectedMealTypes] = useState([]);
    const [selectedDietary, setSelectedDietary] = useState([]);
    const [selectedCuisine, setSelectedCuisine] = useState([]);
    const [selectedOccasion, setSelectedOccasion] = useState([]);
    const searchBarRef = useRef(null);
    const contentRef = useRef(null);
    // One app-wide set of base-recipe ids whose favorite request is in flight
    // (Home card, Favorites base tab and RecipeDetail all share toggleFavorite).
    const favoritePendingRef = useRef(new Set());
    const [filterPanelTop, setFilterPanelTop] = useState(0);

    const [generatedRecipe, setGeneratedRecipe] = useState(null);
    const [generateError, setGenerateError] = useState(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [notificationCount, setNotificationCount] = useState(null);
    const [notificationItems, setNotificationItems] = useState([]);
    const [notificationTab, setNotificationTab] = useState("unread");
    const [notificationCursor, setNotificationCursor] = useState(null);
    const [notificationLoading, setNotificationLoading] = useState(false);
    const [notificationPending, setNotificationPending] = useState(false);
    const [notificationError, setNotificationError] = useState("");
    const [notificationReturnView, setNotificationReturnView] = useState("home");
    const [openedFromNotification, setOpenedFromNotification] = useState(false);
    const [toastQueue, setToastQueue] = useState([]);
    const [profileNotificationPaused, setProfileNotificationPaused] = useState(false);
    const notificationTabRef = useRef("unread");
    const notificationOwnerRef = useRef(user?.id);
    const notificationLoadRef = useRef(0);
    const notificationSyncRef = useRef(false);
    const notificationSyncAgainRef = useRef(false);
    const notificationReadRef = useRef(false);
    const notificationSeenRef = useRef(new Set());
    const notificationScrollRef = useRef({ unread: 0, read: 0 });
    const notificationFridgeRef = useRef("");
    const historyFavoritePendingRef = useRef(new Set());
    const getNotificationScroll = useCallback(tab => notificationScrollRef.current[tab], []);
    const rememberNotificationScroll = useCallback((tab, position) => { notificationScrollRef.current[tab] = position; }, []);

    const enqueueNotification = useCallback(notice => {
        if (!notice || notificationOwnerRef.current !== user?.id) return;
        const records = notice.kind === "expiry_summary" ? notice.items : [notice];
        const fresh = records.filter(record => !record.read_at && !notificationSeenRef.current.has(record.id));
        if (!fresh.length) return;
        fresh.forEach(record => notificationSeenRef.current.add(record.id));
        setToastQueue(queue => [...queue, notice.kind === "expiry_summary" ? { ...notice, items: fresh, id: `expiry:${fresh.map(record => record.id).join(",")}` } : notice]);
    }, [user?.id]);

    const loadNotifications = useCallback(async (tab, cursor = null) => {
        const sequence = ++notificationLoadRef.current;
        setNotificationLoading(true);
        try {
            const response = await apiFetch(`/api/notifications?state=${tab}&limit=20${cursor ? `&before_id=${cursor}` : ""}`);
            const result = await response.json();
            if (!response.ok || result.status !== "success") throw new Error("feed");
            if (sequence !== notificationLoadRef.current || notificationOwnerRef.current !== user?.id) return;
            setNotificationItems(previous => cursor ? [...previous, ...result.data.items.filter(item => !previous.some(old => old.id === item.id))] : result.data.items);
            setNotificationCount(result.data.unread_count);
            setNotificationCursor(result.data.next_before_id);
            setNotificationError("");
        } catch {
            if (sequence === notificationLoadRef.current && notificationOwnerRef.current === user?.id) setNotificationError("โหลดแจ้งเตือนไม่สำเร็จ กรุณาลองอีกครั้ง");
        } finally {
            if (sequence === notificationLoadRef.current && notificationOwnerRef.current === user?.id) setNotificationLoading(false);
        }
    }, [apiFetch, user?.id]);

    const syncNotifications = useCallback(async function sync() {
        if (notificationSyncRef.current) { notificationSyncAgainRef.current = true; return; }
        notificationSyncRef.current = true;
        try {
            const response = await apiFetch("/api/notifications/sync", { method: "POST" });
            const result = await response.json();
            if (!response.ok || result.status !== "success") throw new Error("sync");
            if (notificationOwnerRef.current !== user?.id) return;
            setNotificationCount(result.data.unread_count);
            if (result.data.created_items.length) enqueueNotification({ kind: "expiry_summary", items: result.data.created_items });
            await loadNotifications(notificationTabRef.current);
        } catch {
            if (notificationOwnerRef.current === user?.id) setNotificationError("โหลดแจ้งเตือนไม่สำเร็จ กรุณาลองอีกครั้ง");
        } finally {
            if (notificationOwnerRef.current === user?.id) {
                notificationSyncRef.current = false;
                if (notificationSyncAgainRef.current) {
                    notificationSyncAgainRef.current = false;
                    void sync();
                }
            }
        }
    }, [apiFetch, enqueueNotification, loadNotifications, user?.id]);

    useEffect(() => {
        notificationOwnerRef.current = user?.id;
        let active = true;
        let timer;
        let day = bangkokDate();
        Promise.resolve().then(() => {
            if (!active) return;
            notificationSeenRef.current.clear();
            notificationTabRef.current = "unread";
            notificationScrollRef.current = { unread: 0, read: 0 };
            setNotificationCount(null);
            setNotificationItems([]);
            setNotificationTab("unread");
            setNotificationCursor(null);
            setNotificationError("");
            setToastQueue([]);
        });
        const refresh = async () => {
            if (!active || document.visibilityState === "hidden") return;
            void syncNotifications();
            try {
                const response = await apiFetch("/api/user-ingredients");
                const result = await response.json();
                if (active && response.ok && result.status === "success") setUserIngredients(result.data);
            } catch { /* Existing fridge data remains available on refresh failure. */ }
        };
        const watch = () => {
            clearInterval(timer);
            if (document.visibilityState === "hidden") return;
            day = bangkokDate();
            void refresh();
            timer = setInterval(() => {
                const nextDay = bangkokDate();
                if (nextDay !== day) { day = nextDay; void refresh(); }
            }, 1000);
        };
        watch();
        document.addEventListener("visibilitychange", watch);
        window.addEventListener("focus", refresh);
        const invalidateReads = () => { notificationLoadRef.current++; };
        return () => {
            active = false;
            notificationOwnerRef.current = null;
            invalidateReads();
            notificationSyncRef.current = false;
            notificationSyncAgainRef.current = false;
            notificationFridgeRef.current = "";
            clearInterval(timer);
            document.removeEventListener("visibilitychange", watch);
            window.removeEventListener("focus", refresh);
        };
    }, [apiFetch, syncNotifications, user?.id]);

    useEffect(() => {
        const signature = userIngredients.map(item => `${item.id}:${item.expiry_date ?? ""}`).join("|");
        if (signature === notificationFridgeRef.current) return;
        notificationFridgeRef.current = signature;
        const reconcile = async () => {
            setToastQueue(queue => queue.flatMap(notice => {
                if (notice.kind !== "expiry_summary") return [notice];
                const items = notice.items.filter(item => userIngredients.some(source => source.id === item.target_id && source.expiry_date === item.payload.expiry_date));
                return items.length ? [{ ...notice, items }] : [];
            }));
            await syncNotifications();
        };
        void reconcile();
    }, [userIngredients, syncNotifications]);

    const dismissToast = useCallback(() => setToastQueue(queue => queue.slice(1)), []);
    const openNotifications = () => {
        setNotificationReturnView(currentView);
        setCurrentView("notifications");
        void syncNotifications();
    };
    const changeNotificationTab = tab => {
        notificationTabRef.current = tab;
        setNotificationTab(tab);
        setNotificationItems([]);
        setNotificationCursor(null);
        void loadNotifications(tab);
    };
    const readAllNotifications = async () => {
        if (notificationReadRef.current) return;
        notificationReadRef.current = true;
        setNotificationPending(true);
        try {
            const response = await apiFetch("/api/notifications/read-all", { method: "PUT" });
            const result = await response.json();
            if (!response.ok || result.status !== "success") throw new Error("read");
            if (notificationOwnerRef.current !== user?.id) return;
            setNotificationCount(result.data.unread_count);
            setToastQueue([]);
            await loadNotifications(notificationTabRef.current);
        } catch { if (notificationOwnerRef.current === user?.id) setNotificationError("บันทึกสถานะอ่านไม่สำเร็จ กรุณาลองอีกครั้ง"); }
        finally { notificationReadRef.current = false; if (notificationOwnerRef.current === user?.id) setNotificationPending(false); }
    };
    const openNotificationTarget = async notice => {
        if (notificationReadRef.current) return;
        notificationReadRef.current = true;
        setNotificationPending(true);
        let readConfirmed = false;
        try {
            const read = await apiFetch(`/api/notifications/${notice.id}/read`, { method: "PUT" });
            if (!read.ok) throw new Error("read");
            const readResult = await read.json();
            if (readResult.status !== "success") throw new Error("read");
            if (notificationOwnerRef.current !== user?.id) return;
            readConfirmed = true;
            notificationLoadRef.current++;
            setNotificationLoading(false);
            setNotificationCount(readResult.unread_count);
            setNotificationItems(items => notificationTabRef.current === "unread" ? items.filter(item => item.id !== notice.id) : items.map(item => item.id === notice.id ? readResult.data : item));
            setToastQueue(queue => queue.filter(item => item.kind === "expiry_summary" ? !item.items.some(record => record.id === notice.id) : item.id !== notice.id));
            const url = notice.target_type === "ingredient" ? "/api/user-ingredients" : notice.target_type === "history" ? "/api/history" : "/api/recipes";
            const response = await apiFetch(url);
            const result = await response.json();
            if (notificationOwnerRef.current !== user?.id) return;
            const source = response.ok && result.status === "success" && result.data.find(item => item.id === notice.target_id);
            if (!source) { setNotificationError("รายการนี้เปลี่ยนแปลงหรือไม่พร้อมใช้งานแล้ว"); return; }
            setOpenedFromNotification(true);
            if (notice.target_type === "ingredient") {
                setUserIngredients(result.data);
                setSelectedIngredientDetail(source);
                setCurrentView("ingredient-detail");
            } else if (notice.target_type === "history") {
                setSelectedHistoryItem(toHistoryItem(source));
                setHistoryReturnView("notifications");
                setCurrentView("history-detail");
            } else {
                setSelectedRecipe(source);
                setCurrentView("recipe-detail");
            }
        } catch { if (notificationOwnerRef.current === user?.id) setNotificationError(readConfirmed ? "รายการนี้เปลี่ยนแปลงหรือไม่พร้อมใช้งานแล้ว" : "บันทึกสถานะอ่านไม่สำเร็จ กรุณาลองอีกครั้ง"); }
        finally { notificationReadRef.current = false; if (notificationOwnerRef.current === user?.id) setNotificationPending(false); }
    };

    const rateRecipe = async (historyId, rating) => {
        const session = historySessionRef.current;
        if (!session || session.pending.has(historyId)) return false;
        session.pending.add(historyId);
        try {
            const response = await apiFetch(`/api/history/${historyId}/rating`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    stars: rating.stars,
                    tag: rating.tag,
                    feedback: rating.feedback,
                }),
            });
            if (!response.ok) return false;
            const result = await response.json();
            if (result.status !== "success" || historySessionRef.current !== session) return false;
            setCookingHistory((prev) =>
                prev.map((item) =>
                    item.id === historyId ? { ...item, ...result.data } : item
                )
            );
            setSelectedHistoryItem(item => item?.id === historyId ? { ...item, ...result.data } : item);
            return true;
        } catch (error) {
            console.error("Error saving rating:", error);
            return false;
        } finally {
            session.pending.delete(historyId);
        }
    };

    const toggleHistoryFavorite = async (historyId) => {
        if (historyFavoritePendingRef.current.has(historyId)) return;
        const current = cookingHistory.find((item) => item.id === historyId);
        if (!current) return;
        historyFavoritePendingRef.current.add(historyId);
        const next = !current.is_favorite;
        const setFavorite = (value) =>
            setCookingHistory((prev) =>
                prev.map((item) =>
                    item.id === historyId ? { ...item, is_favorite: value } : item
                )
            );
        setFavorite(next);
        try {
            const response = await apiFetch(`/api/history/${historyId}/favorite`, {
                method: next ? "PUT" : "DELETE",
            });
            const result = await response.json();
            if (!response.ok || result.status !== "success") setFavorite(!next);
            else if (result.notification) { enqueueNotification(result.notification); void loadNotifications(notificationTabRef.current); }
        } catch (error) {
            console.error("Error toggling favorite:", error);
            setFavorite(!next);
        } finally {
            historyFavoritePendingRef.current.delete(historyId);
        }
    };
    const [cookingSource, setCookingSource] = useState("create-recipe"); // "create-recipe" | "custom-cooking"

    useEffect(() => {
        const viewToFile = {
            home: "App.jsx",
            "recipe-detail": "RecipeDetail.jsx",
            "create-recipe": "CreateRecipe.jsx",
            "cooking-page": "CookingPage.jsx",
            "user-ingredients": "UserIngredients.jsx",
            "add-ingredient": "AddIngredient.jsx",
            "barcode-scan": "BarcodeScanPage.jsx",
            "ingredient-detail": "IngredientDetail.jsx",
            "custom-cooking": "CustomCookingPage.jsx",
            favorites: "Favorites.jsx",
            profile: "Profile.jsx",
        };
        console.log("[PAGE]", viewToFile[currentView] ?? currentView);
    }, [currentView]);

    useEffect(() => {
        const fetchRecipes = async () => {
            try {
                const response = await fetch(
                    "/api/recipes",
                );
                const result = await response.json();
                if (result.status === "success") {
                    setRecipes(result.data);

                    const allTags = new Set(["All"]);
                    result.data.forEach((recipe) => {
                        if (recipe.tags && Array.isArray(recipe.tags)) {
                            recipe.tags.forEach((tag) => allTags.add(tag));
                        }
                    });
                    setCategories(Array.from(allTags));
                }
            } catch (error) {
                console.error("Error fetching recipes:", error);
            }
        };

        const fetchUserIngredients = async () => {
            try {
                const response = await apiFetch("/api/user-ingredients");
                const result = await response.json();
                if (result.status === "success") {
                    setUserIngredients(result.data);
                }
            } catch (error) {
                console.error("Error fetching user ingredients:", error);
            }
        };

        const fetchHistory = async () => {
            const session = historySessionRef.current;
            try {
                const response = await apiFetch("/api/history");
                if (!response.ok) return;
                const result = await response.json();
                if (result.status === "success" && session === historySessionRef.current) {
                    setCookingHistory(result.data.map(toHistoryItem));
                }
            } catch (error) {
                console.error("Error fetching cooking history:", error);
            }
        };

        const fetchBaseFavorites = async () => {
            try {
                const response = await apiFetch("/api/base-favorites");
                if (!response.ok) return;
                const result = await response.json();
                if (result.status === "success") {
                    setFavoriteRecipeIds(result.data);
                }
            } catch (error) {
                console.error("Error fetching base favorites:", error);
            }
        };

        fetchRecipes();
        fetchUserIngredients();
        fetchHistory();
        fetchBaseFavorites();
    }, [apiFetch]);

    const FILTER_TABS = [
        { key: "ingredient", label: "Ingredient" },
        { key: "mealType", label: "Meal Type" },
        { key: "dietary", label: "Dietary" },
        { key: "cuisine", label: "Cuisine" },
        { key: "occasion", label: "Occasion" },
    ];
    const MEAL_TYPE_OPTIONS = ["Breakfast", "Brunch", "Lunch", "Dinner"];
    const DIETARY_OPTIONS = ["Vegetarian", "Vegan", "Glutan Free", "Low Carb"];
    const CUISINE_OPTIONS = ["British", "Thai", "Japan", "American"];
    const OCCASION_OPTIONS = ["Date Night", "Kid-Friendly", "Picnic"];
    const OPTION_EMOJI = {
        Breakfast: "🍳",
        Brunch: "🥐",
        Lunch: "🍱",
        Dinner: "🍽️",
        Vegetarian: "🥦",
        Vegan: "🌱",
        "Glutan Free": "🌾",
        "Low Carb": "🥑",
        British: "🇬🇧",
        Thai: "🇹🇭",
        Japan: "🇯🇵",
        American: "🇺🇸",
        "Date Night": "🌹",
        "Kid-Friendly": "🧒",
        Picnic: "🧺",
    };

    const filterCounts = {
        ingredient: selectedIngredientNames.length,
        mealType: selectedMealTypes.length,
        dietary: selectedDietary.length,
        cuisine: selectedCuisine.length,
        occasion: selectedOccasion.length,
    };

    const allIngredients = useMemo(() => {
        const map = new Map();
        recipes.forEach((recipe) => {
            (recipe.ingredients || []).forEach((ing) => {
                const key = (ing.name || "").toLowerCase().trim();
                if (key && !map.has(key)) {
                    map.set(key, { name: key, image: ing.image });
                }
            });
        });
        return Array.from(map.values());
    }, [recipes]);

    const visibleIngredients = allIngredients.filter((ing) =>
        ing.name.includes(filterIngredientQuery.trim().toLowerCase()),
    );
    const selectedIngredientObjs = allIngredients.filter((ing) =>
        selectedIngredientNames.includes(ing.name),
    );

    useLayoutEffect(() => {
        if (showFilterPanel && searchBarRef.current) {
            setFilterPanelTop(
                searchBarRef.current.offsetTop + searchBarRef.current.offsetHeight,
            );
        }
    }, [showFilterPanel]);

    const toggleInList = (value, list, setList) => {
        setList(
            list.includes(value)
                ? list.filter((v) => v !== value)
                : [...list, value],
        );
    };

    const openFilterPanel = () => {
        if (contentRef.current) contentRef.current.scrollTop = 0;
        setShowFilterPanel(true);
    };

    const clearFilters = () => {
        setSelectedIngredientNames([]);
        setSelectedMealTypes([]);
        setSelectedDietary([]);
        setSelectedCuisine([]);
        setSelectedOccasion([]);
        setFilterIngredientQuery("");
    };

    // Optimistic, persisted toggle for base-recipe favorites. Ignores taps while
    // a request for the same id is in flight; on failure restores the id's
    // previous membership (not a blind flip).
    const toggleFavorite = async (recipeId) => {
        if (favoritePendingRef.current.has(recipeId)) return;
        const wasFavorite = favoriteRecipeIds.includes(recipeId);
        favoritePendingRef.current.add(recipeId);

        const setMembership = (isMember) => {
            setFavoriteRecipeIds((prev) => {
                const without = prev.filter((id) => id !== recipeId);
                return isMember ? [...without, recipeId] : without;
            });
        };

        setMembership(!wasFavorite);
        try {
            const response = await apiFetch(
                "/api/base-favorites/" + recipeId,
                { method: wasFavorite ? "DELETE" : "PUT" },
            );
            if (!response.ok) {
                setMembership(wasFavorite);
                return;
            }
            const result = await response.json();
            if (result.status !== "success") {
                setMembership(wasFavorite);
            } else if (result.notification) {
                enqueueNotification(result.notification);
                void loadNotifications(notificationTabRef.current);
            }
        } catch (error) {
            console.error("Error toggling base favorite:", error);
            setMembership(wasFavorite);
        } finally {
            favoritePendingRef.current.delete(recipeId);
        }
    };

    const selectedTagFilters = [
        ...selectedMealTypes,
        ...selectedDietary,
        ...selectedCuisine,
        ...selectedOccasion,
    ].map((t) => t.toLowerCase());

    const filteredRecipes = recipes.filter((recipe) => {
        if (
            selectedCategory !== "All" &&
            !(recipe.tags && recipe.tags.includes(selectedCategory))
        )
            return false;

        const searchLower = searchQuery.trim().toLowerCase();
        if (searchLower && !recipe.name.toLowerCase().includes(searchLower))
            return false;

        if (selectedIngredientNames.length > 0) {
            const recipeIngNames = (recipe.ingredients || []).map((i) =>
                (i.name || "").toLowerCase(),
            );
            if (
                !selectedIngredientNames.some((n) =>
                    recipeIngNames.includes(n),
                )
            )
                return false;
        }

        if (selectedTagFilters.length > 0) {
            const recipeTagsLower = (recipe.tags || []).map((t) =>
                t.toLowerCase(),
            );
            if (!selectedTagFilters.some((t) => recipeTagsLower.includes(t)))
                return false;
        }

        return true;
    });

    const handleTabChange = (tab) => {
        setOpenedFromNotification(false);
        setActiveTab(tab);
        if (tab === "home") {
            setCurrentView("home");
            setSelectedRecipe(null);
        } else if (tab === "fridge") {
            setCurrentView("user-ingredients");
        } else if (tab === "favorites") {
            setCurrentView("favorites");
        } else if (tab === "me") {
            setProfileView("main");
            setCurrentView("profile");
        } else if (tab === "cooking" && [
            "home", "user-ingredients", "add-ingredient", "barcode-scan",
            "ingredient-detail", "favorites", "profile",
        ].includes(currentView)) {
            setSelectedRecipe(null);
            setCurrentView("custom-cooking");
        }
    };

    const renderPage = () => {
    if (currentView === "notifications") {
        return <Notifications items={notificationItems} ingredients={userIngredients} count={notificationCount} tab={notificationTab}
            onTabChange={changeNotificationTab} loading={notificationLoading} pending={notificationPending}
            error={notificationError} nextCursor={notificationCursor}
            onLoadMore={() => loadNotifications(notificationTabRef.current, notificationCursor)}
            onRetry={syncNotifications} onReadAll={readAllNotifications} onOpen={openNotificationTarget}
            onBack={() => setCurrentView(notificationReturnView)} activeTab={activeTab} setActiveTab={handleTabChange}
            getScroll={getNotificationScroll} rememberScroll={rememberNotificationScroll} />;
    }
    if (currentView === "recipe-detail") {
        return (
            <RecipeDetail
                recipe={selectedRecipe}
                isFavorite={favoriteRecipeIds.includes(selectedRecipe?.id)}
                onToggleFavorite={toggleFavorite}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => {
                    setCurrentView(openedFromNotification ? "notifications" : "home");
                    if (!openedFromNotification) setActiveTab("home");
                }}
                onConfirm={(ingredients) => {
                    setSelectedIngredients(ingredients);
                    setCurrentView("create-recipe");
                    setActiveTab("cooking");
                }}
            />
        );
    }

    if (currentView === "create-recipe") {
        return (
            <CreateRecipe
                recipe={selectedRecipe}
                selectedIngredients={selectedIngredients}
                userIngredients={userIngredients}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => setCurrentView("recipe-detail")}
                onGenerate={async (preferences, updatedIngredients) => {
                    const preferenceError = await validateAllergyPreferences(apiFetch, preferences);
                    if (preferenceError) return preferenceError;
                    setCurrentView("cooking-page");
                    setCookingSource("create-recipe");
                    setGeneratedRecipe(null);
                    setGenerateError(null);
                    setIsGenerating(true);
                    try {
                        const response = await apiFetch("/api/generate-recipe-text", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                recipe: selectedRecipe,
                                ingredients: toPresenceIngredients(
                                    updatedIngredients || selectedIngredients,
                                ),
                                preferences
                            })
                        });
                        const result = await response.json();
                        if (response.ok && result.status === "success") {
                            const historyId = result.data.history_id ?? null;
                            setGeneratedRecipe({ ...result.data, _historyId: historyId });
                            if (historyId !== null) {
                                enqueueNotification(result.notification);
                                void loadNotifications(notificationTabRef.current);
                                setCookingHistory((prev) => [
                                    {
                                        ...result.data,
                                        id: historyId,
                                        image: selectedRecipe?.image || null,
                                        is_favorite: false,
                                        stars: 0,
                                        tag: null,
                                        feedback: null,
                                    },
                                    ...prev,
                                ]);
                            }
                        } else {
                            console.error("Failed to generate:", result.message);
                            setGenerateError(toUserFacingGenerateError(result.message, locale));
                        }
                    } catch (err) {
                        console.error("Error generating recipe text:", err);
                    } finally {
                        setIsGenerating(false);
                    }
                }}
            />
        );
    }

    if (currentView === "cooking-page") {
        return (
            <CookingPage
                recipe={selectedRecipe}
                generatedRecipe={generatedRecipe}
                generateError={generateError}
                isGenerating={isGenerating}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => setCurrentView(cookingSource)}
                isCustom={cookingSource === "custom-cooking"}
                onRateRecipe={rateRecipe}
                historyItem={
                    cookingHistory.find(
                        (item) => item.id === generatedRecipe?._historyId
                    ) || null
                }
                onToggleFavorite={toggleHistoryFavorite}
            />
        );
    }

    if (currentView === "user-ingredients") {
        return (
            <UserIngredients
                notificationCount={notificationCount} onNotifications={openNotifications}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                userIngredients={userIngredients}
                onAddManually={() => {
                    setBarcodePrefill(null);
                    setCurrentView("add-ingredient");
                }}
                onScanBarcode={() => setCurrentView("barcode-scan")}
                onOpenIngredient={(ing) => {
                    setSelectedIngredientDetail(ing);
                    setCurrentView("ingredient-detail");
                }}
                onBack={() => {
                    setCurrentView("home");
                    setActiveTab("home");
                }}
            />
        );
    }

    if (currentView === "ingredient-detail") {
        return (
            <IngredientDetail
                key={selectedIngredientDetail?.id}
                ingredient={selectedIngredientDetail}
                userIngredients={userIngredients}
                setUserIngredients={setUserIngredients}
                onUpdated={setSelectedIngredientDetail}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => {
                    setSelectedIngredientDetail(null);
                    setCurrentView(openedFromNotification ? "notifications" : "user-ingredients");
                }}
                onDeleted={() => {
                    setSelectedIngredientDetail(null);
                    setCurrentView("user-ingredients");
                }}
            />
        );
    }

    if (currentView === "barcode-scan") {
        return (
            <BarcodeScanPage
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => setCurrentView("user-ingredients")}
                onScanned={(data) => {
                    setBarcodePrefill(data);
                    setCurrentView("add-ingredient");
                }}
                onAddManually={() => {
                    setBarcodePrefill(null);
                    setCurrentView("add-ingredient");
                }}
            />
        );
    }

    if (currentView === "favorites") {
        return (
            <Favorites
                notificationCount={notificationCount} onNotifications={openNotifications}
                recipes={recipes}
                categories={categories}
                favoriteRecipeIds={favoriteRecipeIds}
                toggleFavorite={toggleFavorite}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => {
                    setCurrentView("home");
                    setActiveTab("home");
                }}
                onSelectRecipe={(recipe) => {
                    setSelectedRecipe(recipe);
                    setActiveTab("cooking");
                    setCurrentView("recipe-detail");
                }}
                tab={favoritesTab}
                onTabChange={setFavoritesTab}
                historyFavorites={cookingHistory.filter((item) => item.is_favorite)}
                onToggleHistoryFavorite={toggleHistoryFavorite}
                onOpenHistoryItem={(item) => {
                    setSelectedHistoryItem(item);
                    setHistoryReturnView("favorites");
                    setCurrentView("history-detail");
                }}
            />
        );
    }

    if (currentView === "add-ingredient") {
        return (
            <AddIngredient
                userIngredients={userIngredients}
                setUserIngredients={setUserIngredients}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                prefill={barcodePrefill}
                onBack={() => setCurrentView("user-ingredients")}
            />
        );
    }

    if (currentView === "custom-cooking") {
        return (
            <CustomCookingPage
                notificationCount={notificationCount} onNotifications={openNotifications}
                userIngredients={userIngredients}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => {
                    setCurrentView("home");
                    setActiveTab("home");
                }}
                onGenerate={async (preferences, selectedIngredients) => {
                    const preferenceError = await validateAllergyPreferences(apiFetch, preferences);
                    if (preferenceError) return preferenceError;
                    setCurrentView("cooking-page");
                    setCookingSource("custom-cooking");
                    setGeneratedRecipe(null);
                    setGenerateError(null);
                    setIsGenerating(true);
                    try {
                        const response = await apiFetch("/api/generate-recipe-text", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                recipe: { name: "Custom Recipe from Fridge" },
                                ingredients: toPresenceIngredients(selectedIngredients),
                                preferences
                            })
                        });
                        const result = await response.json();
                        if (response.ok && result.status === "success") {
                            const historyId = result.data.history_id ?? null;
                            setGeneratedRecipe({ ...result.data, _historyId: historyId });
                            if (historyId !== null) {
                                enqueueNotification(result.notification);
                                void loadNotifications(notificationTabRef.current);
                                setCookingHistory((prev) => [
                                    {
                                        ...result.data,
                                        id: historyId,
                                        image: null,
                                        is_favorite: false,
                                        stars: 0,
                                        tag: null,
                                        feedback: null,
                                    },
                                    ...prev,
                                ]);
                            }
                        } else {
                            console.error("Failed to generate:", result.message);
                            setGenerateError(toUserFacingGenerateError(result.message, locale));
                        }
                    } catch (err) {
                        console.error("Error generating recipe text:", err);
                    } finally {
                        setIsGenerating(false);
                    }
                }}
            />
        );
    }

    if (currentView === "profile") {
        return (
            <Profile
                view={profileView} setView={setProfileView}
                historyBrowse={historyBrowse} setHistoryBrowse={setHistoryBrowse}
                notificationCount={notificationCount} onNotifications={openNotifications}
                onNotificationPause={setProfileNotificationPaused}
                cookingHistory={cookingHistory}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => {
                    setCurrentView("home");
                    setActiveTab("home");
                }}
                onOpenHistoryItem={(item) => {
                    setSelectedHistoryItem(item);
                    setHistoryReturnView("profile");
                    setCurrentView("history-detail");
                }}
            />
        );
    }

    if (currentView === "history-detail") {
        return (
            <HistoryDetail
                key={selectedHistoryItem?.id}
                item={selectedHistoryItem}
                onRateRecipe={rateRecipe}
                activeTab={activeTab}
                setActiveTab={handleTabChange}
                onBack={() => setCurrentView(historyReturnView)}
            />
        );
    }

    return (
        // พื้นหลังสีเทา เพื่อให้ตัวแอปสีขาวโดดเด่นขึ้นมา (เวลาเปิดบนคอม)
        <div className="h-screen bg-gray-100 flex justify-center font-sans overflow-hidden">
            {/* 📱 กล่องแอปพลิเคชัน (จำกัดความกว้างเป็นทรงมือถือ) */}
            <div className="w-full max-w-107.5 bg-white h-full relative overflow-hidden flex flex-col shadow-2xl">
                {/* === เนื้อหาหลักของแอป (Content) === */}
                <div
                    ref={contentRef}
                    className="flex-1 overflow-y-auto pb-24 px-5 pt-8 scrollbar-hide"
                >
                    {/* Logo */}
                    <div className="flex justify-center mb-6 relative">
                        <NotificationBell count={notificationCount} onClick={openNotifications} />
                        <img
                            src={logo}
                            alt="HomeMade"
                            className="h-18 object-contain"
                        />
                    </div>

                    {/* Search Bar */}
                    <div ref={searchBarRef} className="flex items-center gap-3 mb-6">
                        <div className="flex-1 flex items-center bg-white border border-gray-400 rounded-full px-4 py-3">
                            <Search className="w-5 h-5 text-gray-500 mr-2" />
                            <input
                                type="text"
                                placeholder={t("Find the menu")}
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full outline-none text-gray-600 bg-transparent text-base"
                            />
                        </div>
                        <button
                            onClick={openFilterPanel}
                            className="bg-[#EF5A3A] p-3 rounded-full text-white shadow-sm hover:bg-orange-600 transition relative"
                        >
                            <SlidersHorizontal className="w-5 h-5" />
                            {Object.values(filterCounts).some((c) => c > 0) && (
                                <span className="absolute -top-1 -right-1 w-3 h-3 bg-gray-900 rounded-full border-2 border-white"></span>
                            )}
                        </button>
                    </div>

                    {/* Banner */}
                    <div className="w-full h-48 bg-black rounded-3xl mb-6 relative overflow-hidden shadow-sm flex items-center">
                        <img
                            src="https://images.unsplash.com/photo-1555939594-58d7cb561ad1?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
                            alt={t("Cooking Banner")}
                            className="absolute inset-0 w-full h-full object-cover opacity-60"
                        />
                        <div className="absolute inset-0 bg-linear-to-r from-black/80 to-transparent z-0"></div>
                        <div className="relative z-10 text-white w-3/4 pl-6">
                            <h2 className="text-[34px] font-black italic text-white leading-none drop-shadow-[0_2px_2px_rgba(0,0,0,0.8)]">{t("TOP 10")}</h2>
                            <h2 className="text-[34px] font-black italic text-yellow-400 leading-none drop-shadow-[0_2px_2px_rgba(0,0,0,0.8)]">{t("COOKING")}</h2>
                            <h2 className="text-[34px] font-black italic text-yellow-400 leading-none drop-shadow-[0_2px_2px_rgba(0,0,0,0.8)]">{t("RECIPES")}</h2>
                        </div>
                    </div>

                    {/* Categories */}
                    <h3 className="text-lg font-bold text-gray-900 mb-4">{t("Categories")}</h3>
                    <DragScrollRow id="home-categories" className="flex gap-3 pb-2 mb-6 -mx-5 px-5 scrollbar-hide">
                        {categories.map((category, index) => (
                            <button
                                key={index}
                                onClick={() => setSelectedCategory(category)}
                                aria-pressed={selectedCategory === category}
                                className={`min-h-11 shrink-0 max-w-full px-5 py-2 rounded-full text-sm font-medium whitespace-nowrap shadow-sm transition cursor-grab active:cursor-grabbing focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B93E25] ${
                                    selectedCategory === category
                                        ? "bg-[#EF5A3A] text-white"
                                        : "bg-white border border-[#EF5A3A] text-[#EF5A3A] hover:bg-orange-50"
                                }`}
                            >
                                {t(category)}
                            </button>
                        ))}
                    </DragScrollRow>

                    {/* Recipe Cards */}
                    <div className="grid grid-cols-2 gap-4">
                        {filteredRecipes.map((recipe) => (
                            <div
                                key={recipe.id}
                                className="bg-white border border-gray-100 rounded-3xl p-3 shadow-sm relative group cursor-pointer"
                                onClick={() => {
                                    setSelectedRecipe(recipe);
                                    setActiveTab("cooking");
                                    setCurrentView("recipe-detail");
                                }}
                            >
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        toggleFavorite(recipe.id);
                                    }}
                                    className={`absolute top-4 right-4 z-10 ${
                                        favoriteRecipeIds.includes(recipe.id)
                                            ? "text-red-500"
                                            : "text-gray-300 hover:text-red-500"
                                    }`}
                                >
                                    <Heart
                                        className={`w-6 h-6 ${favoriteRecipeIds.includes(recipe.id) ? "fill-current" : ""}`}
                                    />
                                </button>
                                <div className="w-full aspect-square bg-gray-100 rounded-full mb-3 overflow-hidden">
                                    <img
                                        src={recipe.image}
                                        alt={recipe.name}
                                        className="w-full h-full object-cover"
                                    />
                                </div>
                                <h4 className="font-bold text-gray-800 mb-2 truncate">
                                    {recipe.name}
                                </h4>
                                <div className="flex flex-col gap-1 mb-4">
                                    {recipe.tags &&
                                        recipe.tags
                                            .slice(0, 2)
                                            .map((tag, idx) => (
                                                <span
                                                    key={idx}
                                                    className={`text-[10px] font-medium px-2 py-0.5 rounded-full w-max ${getTagColor(tag)}`}
                                                >
                                                    {tag}
                                                </span>
                                            ))}
                                </div>
                                <button className="absolute bottom-3 right-3 bg-gray-900 text-white p-2 rounded-full shadow-md">
                                    <Plus className="w-5 h-5" />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* === Filter Panel === */}
                {showFilterPanel && (
                    <>
                        <div
                            className="absolute inset-0 bg-black/30 z-30"
                            onClick={() => setShowFilterPanel(false)}
                        ></div>
                        <div
                            className="absolute left-0 right-0 bottom-0 bg-white rounded-t-3xl shadow-[0_-10px_40px_rgba(0,0,0,0.1)] z-40 flex flex-col"
                            style={{ top: filterPanelTop }}
                        >
                            <p className="text-xs text-gray-400 font-medium px-5 pt-4">{t("Explore recipe by")}</p>

                            {/* Tab badges */}
                            <DragScrollRow
                                className="flex gap-2 overflow-x-auto scrollbar-hide px-5 py-3 cursor-grab active:cursor-grabbing select-none"
                            >
                                {FILTER_TABS.map((tab) => (
                                    <button
                                        key={tab.key}
                                        onClick={() => setFilterTab(tab.key)}
                                        className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition ${
                                            filterTab === tab.key
                                                ? "bg-[#EF5A3A] text-white"
                                                : "bg-white border border-gray-300 text-gray-600"
                                        }`}
                                    >
                                        {t(tab.label)}
                                        {filterCounts[tab.key] > 0 &&
                                            ` (${filterCounts[tab.key]})`}
                                    </button>
                                ))}
                            </DragScrollRow>

                            {/* Tab content */}
                            <div className="flex-1 overflow-y-auto px-5 pb-4 scrollbar-hide">
                                {filterTab === "ingredient" && (
                                    <>
                                        <div className="flex items-center bg-gray-100 rounded-full px-4 py-2.5 mb-4">
                                            <Search className="w-4 h-4 text-gray-400 mr-2" />
                                            <input
                                                type="text"
                                                placeholder={t("Search ingredient")}
                                                value={filterIngredientQuery}
                                                onChange={(e) =>
                                                    setFilterIngredientQuery(
                                                        e.target.value,
                                                    )
                                                }
                                                className="w-full outline-none bg-transparent text-sm text-gray-600"
                                            />
                                        </div>

                                        {selectedIngredientObjs.length > 0 && (
                                            <div className="mb-4">
                                                <h4 className="text-sm font-bold text-gray-700 mb-2">{t("Selected")}</h4>
                                                <div className="grid grid-cols-4 gap-3">
                                                    {selectedIngredientObjs.map(
                                                        (ing) => (
                                                            <button
                                                                key={ing.name}
                                                                onClick={() =>
                                                                    toggleInList(
                                                                        ing.name,
                                                                        selectedIngredientNames,
                                                                        setSelectedIngredientNames,
                                                                    )
                                                                }
                                                                className="flex flex-col items-center gap-1"
                                                            >
                                                                <div className="relative w-14 h-14">
                                                                    <div className="w-14 h-14 rounded-full overflow-hidden bg-gray-100">
                                                                        <img
                                                                            src={
                                                                                ing.image
                                                                            }
                                                                            alt={
                                                                                ing.name
                                                                            }
                                                                            className="w-full h-full object-cover"
                                                                        />
                                                                    </div>
                                                                    <span className="absolute -top-1 -right-1 w-5 h-5 bg-gray-900 text-white rounded-full flex items-center justify-center border-2 border-white">
                                                                        <X className="w-3 h-3" />
                                                                    </span>
                                                                </div>
                                                                <span className="text-[11px] text-gray-700 capitalize text-center truncate w-full">
                                                                    {ing.name}
                                                                </span>
                                                            </button>
                                                        ),
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        <h4 className="text-sm font-bold text-gray-700 mb-2">{t("All Ingredient")}</h4>
                                        <div className="grid grid-cols-4 gap-3">
                                            {visibleIngredients.map((ing) => {
                                                const isSelected =
                                                    selectedIngredientNames.includes(
                                                        ing.name,
                                                    );
                                                return (
                                                    <button
                                                        key={ing.name}
                                                        onClick={() =>
                                                            toggleInList(
                                                                ing.name,
                                                                selectedIngredientNames,
                                                                setSelectedIngredientNames,
                                                            )
                                                        }
                                                        className="flex flex-col items-center gap-1"
                                                    >
                                                        <div
                                                            className={`w-14 h-14 rounded-full overflow-hidden bg-gray-100 ${
                                                                isSelected
                                                                    ? "opacity-40"
                                                                    : ""
                                                            }`}
                                                        >
                                                            <img
                                                                src={
                                                                    ing.image
                                                                }
                                                                alt={ing.name}
                                                                className="w-full h-full object-cover"
                                                            />
                                                        </div>
                                                        <span
                                                            className={`text-[11px] capitalize text-center truncate w-full ${
                                                                isSelected
                                                                    ? "text-gray-400"
                                                                    : "text-gray-700"
                                                            }`}
                                                        >
                                                            {ing.name}
                                                        </span>
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </>
                                )}

                                {filterTab === "mealType" && (
                                    <FilterCheckboxList
                                        emojiMap={OPTION_EMOJI}
                                        options={MEAL_TYPE_OPTIONS}
                                        selected={selectedMealTypes}
                                        onToggle={(v) =>
                                            toggleInList(
                                                v,
                                                selectedMealTypes,
                                                setSelectedMealTypes,
                                            )
                                        }
                                    />
                                )}

                                {filterTab === "dietary" && (
                                    <FilterCheckboxList
                                        emojiMap={OPTION_EMOJI}
                                        options={DIETARY_OPTIONS}
                                        selected={selectedDietary}
                                        onToggle={(v) =>
                                            toggleInList(
                                                v,
                                                selectedDietary,
                                                setSelectedDietary,
                                            )
                                        }
                                    />
                                )}

                                {filterTab === "cuisine" && (
                                    <FilterCheckboxList
                                        emojiMap={OPTION_EMOJI}
                                        options={CUISINE_OPTIONS}
                                        selected={selectedCuisine}
                                        onToggle={(v) =>
                                            toggleInList(
                                                v,
                                                selectedCuisine,
                                                setSelectedCuisine,
                                            )
                                        }
                                    />
                                )}

                                {filterTab === "occasion" && (
                                    <FilterCheckboxList
                                        emojiMap={OPTION_EMOJI}
                                        options={OCCASION_OPTIONS}
                                        selected={selectedOccasion}
                                        onToggle={(v) =>
                                            toggleInList(
                                                v,
                                                selectedOccasion,
                                                setSelectedOccasion,
                                            )
                                        }
                                    />
                                )}
                            </div>

                            {/* Clear / Apply */}
                            <div className="flex items-center gap-3 px-5 py-4 pb-24 border-t border-gray-100">
                                <button
                                    onClick={clearFilters}
                                    className="flex-1 py-3 rounded-full text-sm font-bold text-gray-600 border border-gray-300"
                                >{t("Clear")}</button>
                                <button
                                    onClick={() => setShowFilterPanel(false)}
                                    className="flex-1 py-3 rounded-full text-sm font-bold text-white bg-[#EF5A3A] shadow-md hover:bg-orange-600 transition"
                                >{t("Apply")}</button>
                            </div>
                        </div>
                    </>
                )}

                {/* === 🔘 Bottom Navigation (แถบเมนูด้านล่าง) === */}
                <BottomMenu
                    activeTab={activeTab}
                    setActiveTab={handleTabChange}
                />
            </div>
        </div>
    );
    };
    const notice = toastQueue[0];
    const showToast = notice && !isGenerating && !showFilterPanel &&
        ["home", "user-ingredients", "favorites", "profile"].includes(currentView) &&
        !(currentView === "profile" && profileNotificationPaused);
    return <>{renderPage()}{showToast && <NotificationToast key={notice.id} notice={notice} ingredients={userIngredients} onDismiss={dismissToast}
        onOpen={() => { dismissToast(); if (notice.kind === "expiry_summary") openNotifications(); else { setNotificationReturnView(currentView); setCurrentView("notifications"); void openNotificationTarget(notice); } }} />}</>;
}

function FilterCheckboxList({ options, selected, onToggle, emojiMap }) {
    const { t } = useLocale();
    return (
        <div className="flex flex-col gap-3">
            {options.map((option) => {
                const isChecked = selected.includes(option);
                return (
                    <div
                        key={option}
                        onClick={() => onToggle(option)}
                        className="flex items-center justify-between bg-gray-100 p-3 rounded-2xl cursor-pointer"
                    >
                        <span className="font-medium text-black text-[15px]">
                            {emojiMap?.[option] && (
                                <span className="mr-2">{emojiMap[option]}</span>
                            )}
                            {t(option)}
                        </span>
                        <div
                            className={`w-6 h-6 rounded flex items-center justify-center transition-colors ${
                                isChecked
                                    ? "bg-gray-800"
                                    : "bg-white border-2 border-gray-300"
                            }`}
                        >
                            {isChecked && (
                                <svg
                                    className="w-4 h-4 text-white"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth="3"
                                        d="M5 13l4 4L19 7"
                                    />
                                </svg>
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

export default function AccountApp() {
    const { user } = useAuth();
    return <App key={user?.id ?? "anonymous"} />;
}
