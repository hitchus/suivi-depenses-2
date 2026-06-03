-keep class com.bydcam.app.byd.** { *; }
-keep class com.bydcam.app.server.** { *; }
-keepattributes Signature
-keepattributes *Annotation*
# NanoHTTPD
-keep class fi.iki.elonen.** { *; }
# Gson
-keepclassmembers class * { @com.google.gson.annotations.SerializedName <fields>; }
# Reflection pour le SDK BYD
-keep class android.os.IAccModeManager { *; }
-keepclassmembers class ** { native <methods>; }
