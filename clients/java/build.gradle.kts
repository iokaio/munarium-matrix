// SPDX-License-Identifier: Apache-2.0
// Official Java client for Munarium Matrix — the structured-evidence plane.
// In-repo library, never published to a registry (Apache-2.0).
//
// ONE dependency: Jackson databind. REST rides java.net.http, which ships with
// the JDK, and the tests drive a `com.sun.net.httpserver` stub rather than
// pulling in a mock-server library — a client whose dependency list is one
// line cannot break a consumer's build over a transitive conflict.
//
// There are deliberately NO protobuf or gRPC dependencies here, and no protobuf
// plugin. Matrix's gRPC plane serves `MatrixQuery/Execute` alone and that call
// is service-to-service: the munarium-server makes it while answering a turn,
// carrying a session's authorization snapshot an application does not hold.
// Generating stubs for it would put ~15 MB of transitive netty on every
// consumer's classpath to expose a call none of them may make. If Matrix ever
// grows a second RPC that an application is entitled to, this file grows a
// transport — not a second client.
//
// Bytecode targets Java 21 (LTS: records, virtual threads) while building on
// any newer JDK via `--release`; the dev box runs a newer JDK than 21.

plugins {
    `java-library`
}

group = "io.ioka.munarium"
version = "1.0.0"

repositories {
    mavenCentral()
}

val jacksonVersion = "2.19.0"
val junitVersion = "5.12.2"

dependencies {
    // `api`, not `implementation`: JsonNode appears in the public surface for
    // the reads whose shape is genuinely open (introspect, the journal), so a
    // consumer must be able to name the type.
    api("com.fasterxml.jackson.core:jackson-databind:$jacksonVersion")

    testImplementation("org.junit.jupiter:junit-jupiter:$junitVersion")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

java {
    sourceCompatibility = JavaVersion.VERSION_21
}

tasks.withType<JavaCompile>().configureEach {
    options.release = 21
    options.encoding = "UTF-8"
    // No generated sources compile in this unit, so -Werror is affordable
    // here in a way it is not in the server client.
    options.compilerArgs.addAll(listOf("-Xlint:all,-processing,-this-escape", "-Werror", "-parameters"))
}

tasks.test {
    useJUnitPlatform()
    // `skipped` and the standard streams are both on so the live tier's
    // out-loud skip actually reaches the console. A skip that prints nothing
    // is indistinguishable from a pass.
    testLogging {
        events("passed", "failed", "skipped")
        showStandardStreams = true
    }
}
