package com.bydcam.app.ui

import android.content.Intent
import android.os.Bundle
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity
import com.bydcam.app.R
import com.bydcam.app.server.HttpServer
import com.bydcam.app.services.CameraService

/**
 * Activité principale : affiche la SPA web dans un WebView plein écran.
 *
 * La SPA communique avec le HttpServer embarqué sur localhost:8080.
 * Pas de code UI natif — tout est dans assets/web/.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        startForegroundService(Intent(this, CameraService::class.java))
        setupWebView()
    }

    private fun setupWebView() {
        webView = findViewById(R.id.webview)
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
            cacheMode = WebSettings.LOAD_NO_CACHE
        }
        webView.webViewClient = WebViewClient()

        // Pointe sur le serveur HTTP local (attend qu'il soit prêt)
        webView.postDelayed({
            webView.loadUrl("http://localhost:${HttpServer.PORT}/")
        }, 1_500)
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack()
        else super.onBackPressed()
    }
}
