import { createContext, useContext, useEffect } from "react";
import { useAuth } from "./AuthContext";
import { translate } from "../utils/translations";

const LocaleContext = createContext(null);

export function LocaleProvider({ children }) {
    const { user } = useAuth();
    const locale = user?.locale === "en" ? "en" : "th";
    useEffect(() => { document.documentElement.lang = locale; }, [locale]);
    return <LocaleContext.Provider value={{ locale, t: (text, values) => translate(text, locale, values) }}>{children}</LocaleContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useLocale() {
    const context = useContext(LocaleContext);
    if (!context) throw new Error("useLocale requires LocaleProvider");
    return context;
}
