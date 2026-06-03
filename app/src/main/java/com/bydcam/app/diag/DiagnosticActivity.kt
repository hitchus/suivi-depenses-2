package com.bydcam.app.diag

import android.os.Bundle
import android.text.method.ScrollingMovementMethod
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.bydcam.app.R
import kotlinx.coroutines.*
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Activité de diagnostic Binder BYD.
 *
 * Lance BydServiceProbe sur la head unit et affiche les résultats
 * en temps réel + exporte un rapport dans /sdcard/BydCam/diag/.
 *
 * Lancer via ADB :
 *   adb shell am start -n com.bydcam.app/.diag.DiagnosticActivity
 */
class DiagnosticActivity : AppCompatActivity() {

    private lateinit var tvLog: TextView
    private lateinit var tvSummary: TextView
    private lateinit var btnProbe: Button
    private lateinit var btnServices: Button

    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private val results = mutableListOf<BydServiceProbe.ProbeResult>()
    private val logLines = StringBuilder()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_diagnostic)

        tvLog     = findViewById(R.id.tv_log)
        tvSummary = findViewById(R.id.tv_summary)
        btnProbe  = findViewById(R.id.btn_probe)
        btnServices = findViewById(R.id.btn_services)

        tvLog.movementMethod = ScrollingMovementMethod()

        btnProbe.setOnClickListener { runFullProbe() }
        btnServices.setOnClickListener { listServices() }

        appendLog("Diagnostic BYD Binder prêt.")
        appendLog("Appuyer sur SONDER pour commencer.")
    }

    private fun listServices() {
        scope.launch {
            appendLog("\n── Services BYD disponibles ──")
            val services = withContext(Dispatchers.IO) {
                BydServiceProbe.listAvailableServices()
            }
            if (services.isEmpty()) {
                appendLog("Aucun service BYD trouvé (vérifier permissions)")
            } else {
                services.forEach { appendLog("  ✓ $it") }
            }
            appendLog("Total : ${services.size} services")
        }
    }

    private fun runFullProbe() {
        btnProbe.isEnabled = false
        btnProbe.text = "Sondage en cours..."
        results.clear()
        logLines.clear()
        tvLog.text = ""
        tvSummary.text = ""

        appendLog("=== DÉMARRAGE SONDAGE BINDER BYD ===")
        appendLog("Codes 1..$MAX_CODE par service\n")

        scope.launch {
            withContext(Dispatchers.IO) {
                BydServiceProbe.probeAll { result ->
                    results.add(result)
                    if (result.status == BydServiceProbe.Status.OK) {
                        val line = "[${result.service}] code=${result.code} " +
                            "ints=${result.intValues} str=${result.stringValues} " +
                            "hex=${result.rawHex.take(24)}"
                        launch(Dispatchers.Main) { appendLog(line) }
                    }
                }
            }

            // Interprétation
            val interpretations = BydServiceProbe.interpret(results)
            appendLog("\n════ RÉSULTATS CANDIDATS ════")
            if (interpretations.isEmpty()) {
                appendLog("Aucun candidat identifié automatiquement.")
                appendLog("Consulter le rapport complet.")
            } else {
                interpretations.forEach { i ->
                    appendLog("★ [${i.service}] code=${i.code} → ${i.type}")
                    appendLog("   ${i.description}")
                }
            }

            // Rapport complet
            val reportFile = exportReport(results, interpretations)
            appendLog("\nRapport exporté : ${reportFile?.absolutePath ?: "ERREUR"}")

            updateSummary(results, interpretations)
            btnProbe.isEnabled = true
            btnProbe.text = "Sonder à nouveau"
        }
    }

    private fun exportReport(
        results: List<BydServiceProbe.ProbeResult>,
        interpretations: List<BydServiceProbe.Interpretation>
    ): File? {
        return try {
            val dir = File("/sdcard/BydCam/diag").also { it.mkdirs() }
            val ts = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
            val file = File(dir, "binder_probe_$ts.txt")

            val sb = StringBuilder()
            sb.appendLine("=== BydCam Binder Probe Report ===")
            sb.appendLine("Date : $ts")
            sb.appendLine("Build : ${android.os.Build.MODEL} / ${android.os.Build.VERSION.RELEASE}")
            sb.appendLine()

            sb.appendLine("── SERVICES DISPONIBLES ──")
            BydServiceProbe.listAvailableServices().forEach { sb.appendLine("  $it") }
            sb.appendLine()

            sb.appendLine("── RÉSULTATS BRUTS (OK uniquement) ──")
            results.filter { it.status == BydServiceProbe.Status.OK }.forEach { r ->
                sb.appendLine("[${r.service}] code=${r.code}")
                sb.appendLine("  ints   : ${r.intValues}")
                sb.appendLine("  strings: ${r.stringValues}")
                sb.appendLine("  hex    : ${r.rawHex}")
            }
            sb.appendLine()

            sb.appendLine("── ERREURS SÉCURITÉ ──")
            results.filter { it.status == BydServiceProbe.Status.SECURITY_EXCEPTION }.forEach { r ->
                sb.appendLine("[${r.service}] code=${r.code} → ${r.errorMsg}")
            }
            sb.appendLine()

            sb.appendLine("── CANDIDATS INTERPRÉTÉS ──")
            interpretations.forEach { i ->
                sb.appendLine("★ [${i.service}] code=${i.code} → ${i.type}: ${i.description}")
            }

            file.writeText(sb.toString())
            file
        } catch (e: Exception) {
            null
        }
    }

    private fun updateSummary(
        results: List<BydServiceProbe.ProbeResult>,
        interpretations: List<BydServiceProbe.Interpretation>
    ) {
        val ok  = results.count { it.status == BydServiceProbe.Status.OK }
        val sec = results.count { it.status == BydServiceProbe.Status.SECURITY_EXCEPTION }
        tvSummary.text = "Total: ${results.size} | OK: $ok | SecEx: $sec | Candidats: ${interpretations.size}"
    }

    private fun appendLog(line: String) {
        logLines.appendLine(line)
        tvLog.text = logLines.toString()
        // Auto-scroll
        val layout = tvLog.layout
        if (layout != null) {
            val scrollY = layout.getLineTop(tvLog.lineCount) - tvLog.height
            if (scrollY > 0) tvLog.scrollTo(0, scrollY)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
    }

    companion object {
        private const val MAX_CODE = 30
    }
}
