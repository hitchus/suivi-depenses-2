plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.bydcam.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.bydcam.app"
        minSdk = 25          // BYD DiLink v3 cible
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
    }

    signingConfigs {
        create("release") {
            storeFile = file(System.getenv("KEYSTORE_FILE") ?: "release.jks")
            storePassword = System.getenv("KEYSTORE_PASSWORD") ?: ""
            keyAlias = System.getenv("KEY_ALIAS") ?: "key0"
            keyPassword = System.getenv("KEY_PASSWORD") ?: ""
        }
    }

    buildTypes {
        debug {
            isMinifyEnabled = false
            isDebuggable = true
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("release")
        }
    }

    splits {
        abi {
            isEnable = true
            reset()
            include("arm64-v8a")   // BYD DiLink v3 = arm64 uniquement
            isUniversalApk = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        buildConfig = true
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.lifecycle.service)
    implementation(libs.coroutines.android)
    implementation(libs.okhttp)
    implementation(libs.nanohttpd)
    implementation(libs.java.websocket)
    implementation(libs.gson)
}
