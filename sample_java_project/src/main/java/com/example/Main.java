package com.example;

import org.apache.commons.lang3.StringUtils;

/**
 * A simple class for demonstrating the Fathom search indexer.
 */
public class Main {

    /**
     * The main entry point for the application.
     * It prints a hello message.
     * @param args Command line arguments.
     */
    public static void main(String[] args) {
        System.out.println("Hello from the sample Java project!");
        greet("Fathom");
    }

    /**
     * A simple method that returns a greeting string.
     * This is intended to be indexed by Fathom.
     * @param name The name to include in the greeting.
     * @return A greeting string.
     */
    public static String greet(String name) {
        if (StringUtils.isBlank(name)) {
            return "Hello, stranger!";
        }
        return "Hello, " + name + "!";
    }

    /**
     * A private helper method to demonstrate different access modifiers.
     */
    private void helperMethod() {
        System.out.println("This is a private helper method.");
    }
}
