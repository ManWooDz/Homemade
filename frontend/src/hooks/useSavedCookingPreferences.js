import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { emptyCookingPreferences, loadCookingPreferences, mergeUntouchedPreferences, readCookingPreferences } from "../utils/cookingPreferences.js";

export default function useSavedCookingPreferences() {
    const { apiFetch } = useAuth();
    const [value, setValue] = useState(emptyCookingPreferences);
    const current = useRef(value);
    const touched = useRef(new Set());
    const [status, setStatus] = useState("loading");
    const [attempt, setAttempt] = useState(0);
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const loaded = readCookingPreferences(await loadCookingPreferences(apiFetch));
                if (cancelled) return;
                current.current = mergeUntouchedPreferences(current.current, loaded, touched.current);
                setValue(current.current);
                setStatus("ready");
            } catch {
                if (!cancelled) setStatus("error");
            }
        })();
        return () => { cancelled = true; };
    }, [apiFetch, attempt]);
    const edit = next => {
        for (const key of Object.keys(next)) if (next[key] !== current.current[key]) touched.current.add(key);
        current.current = next;
        setValue(next);
    };
    const retry = () => { setStatus("loading"); setAttempt(count => count + 1); };
    return { value, edit, status, retry };
}
